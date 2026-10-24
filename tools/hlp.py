#!/usr/bin/env python3
"""Read/write the Norton Guides subset used by Volkov Commander's F1 viewer.

This is a VC help compiler, not a Windows WinHelp compiler or a general NG
implementation. The VC short-entry index uses six-byte (text offset, file
offset) references. See help/README.md for the source format and limits.
"""
import argparse
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import struct
import textwrap

HEADER_SIZE = 378
ENTRY = struct.Struct("<HHHHHIHHII")
REFERENCE = struct.Struct("<HI")
NO_OFFSET = 0xffffffff
WIDTH = 64
# HelpBuf holds 12 bytes of viewer state before HlpMode, then the 26-byte
# entry header. HlpEntry rejects sizes greater than OR EQUAL to the rest.
MAX_PAYLOAD = 3000 - 12 - ENTRY.size - 1


def xor(data):
    return bytes(c ^ 0x1a for c in data)


def unpack_spaces(data):
    result = bytearray()
    i = 0
    while i < len(data):
        c = data[i]
        i += 1
        if c == 255:
            if i == len(data) or data[i] == 0 or data[i] > 127:
                raise ValueError("unsupported or truncated space run")
            result.extend(b" " * data[i])
            i += 1
        else:
            result.append(c)
    return bytes(result)


def pack_spaces(data):
    if b"\xff" in data:
        raise ValueError("literal byte FF conflicts with the space-run marker")
    return re.sub(b" {3,}", lambda m: b"".join(
        b"\xff" + bytes([min(127, len(m[0])-i)])
        for i in range(0, len(m[0]), 127)), data)


def read_entry(data, offset):
    if offset < HEADER_SIZE or offset + ENTRY.size > len(data):
        raise ValueError("entry offset outside the help file")
    header = ENTRY.unpack(xor(data[offset:offset+ENTRY.size]))
    end = offset + ENTRY.size + header[1]
    if end > len(data):
        raise ValueError("truncated entry")
    return header, xor(data[offset+ENTRY.size:end])


def read_lines(data, count):
    parts = data.split(b"\0")
    if len(parts) != count+1 or parts[-1]:
        raise ValueError("line count/terminator mismatch")
    return [unpack_spaces(line) for line in parts[:-1]]


def decompile(data, codepage):
    if data[:4] != b"NG\0\1" or len(data) < 408:
        raise ValueError("not a supported VC Norton Guides file")
    root = struct.unpack("<I", xor(data[404:408]))[0]
    header, payload = read_entry(data, root)
    count = header[2]
    if header[0] != 0 or count*REFERENCE.size > len(payload):
        raise ValueError("missing or invalid VC short-entry index")
    titles = read_lines(payload[count*REFERENCE.size:], count)
    topics = []
    title_offset = count*REFERENCE.size
    for i, title in enumerate(titles):
        string_offset, offset = REFERENCE.unpack_from(payload, i*REFERENCE.size)
        if string_offset != title_offset:
            raise ValueError("index text pointer does not match its line")
        raw_title = payload[title_offset:].split(b"\0", 1)[0]
        title_offset += len(raw_title)+1
        th, body = read_entry(data, offset)
        if th[0] != 1 or th[3] != 0:
            raise ValueError("unsupported topic type or see-also records")
        topics.append({"id": f"legacy_{i+1:02}", "title": title.decode(codepage),
                       "lines": [line.decode(codepage) for line in read_lines(body, th[2])]})
    credits = [data[i:i+66].split(b"\0", 1)[0].decode(codepage)
               for i in range(48, HEADER_SIZE, 66)]
    return {"codepage": codepage, "credits": credits, "topics": topics}


def _encode_lines(lines, codepage):
    for line in lines:
        if "\0" in line or "\n" in line or "\r" in line:
            raise ValueError("a help line cannot contain a line terminator")
    return b"".join(pack_spaces(line.encode(codepage)) + b"\0" for line in lines)


def _field(text, size, codepage):
    value = text.encode(codepage)
    if b"\0" in value or len(value) >= size:
        raise ValueError(f"header field must fit in {size-1} bytes")
    return value.ljust(size, b"\0")


def _record(kind, lines, payload, parent=NO_OFFSET, parent_line=65535,
            previous=NO_OFFSET, following=NO_OFFSET):
    if len(payload) > MAX_PAYLOAD or len(lines) > 65535:
        raise ValueError(f"help record exceeds the viewer's {MAX_PAYLOAD}-byte buffer")
    return xor(ENTRY.pack(kind, len(payload), len(lines), 0, parent_line,
                          parent, 0, 0, previous, following) + payload)


def compile_guide(topics, codepage, version, credits=()):
    if not topics or len(topics) > 255:
        raise ValueError("a VC guide needs 1..255 topics")
    ids = [topic["id"] for topic in topics]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate topic id")
    if any(not topic["lines"] for topic in topics):
        raise ValueError("every topic must have at least one terminated line")
    header = struct.pack("<4H", 0x474e, 0x100, 0, 1)
    header += _field(f"VC {version} Help", 40, codepage)
    if len(credits) > 5:
        raise ValueError("at most five credit lines fit in the header")
    header += b"".join(_field(text, 66, codepage) for text in list(credits)+[""]*(5-len(credits)))
    # The menu's first pointer is at 0x194, as expected by HlpRead.
    menu_tail = b"\0"*8 + b"Volkov Commander\0Contents\0"
    root = HEADER_SIZE + ENTRY.size + 4 + len(menu_tail)
    menu = _record(2, ["Contents"], struct.pack("<I", root)+menu_tail,
                   previous=0, following=0)
    labels = _encode_lines([t["title"] for t in topics], codepage)
    payload_size = len(topics)*REFERENCE.size+len(labels)
    if payload_size > MAX_PAYLOAD:
        raise ValueError(f"index needs {payload_size} bytes; maximum is {MAX_PAYLOAD}")
    bodies = [_encode_lines(t["lines"], codepage) for t in topics]
    offsets = []
    cursor = root + ENTRY.size + payload_size
    for topic, body in zip(topics, bodies):
        if len(body) > MAX_PAYLOAD:
            raise ValueError(f"topic {topic['id']} needs {len(body)} bytes; maximum is {MAX_PAYLOAD}")
        offsets.append(cursor)
        cursor += ENTRY.size + len(body)
    references = bytearray()
    title_offset = len(topics)*REFERENCE.size
    for label, offset in zip(labels.split(b"\0")[:-1], offsets):
        references += REFERENCE.pack(title_offset, offset)
        title_offset += len(label)+1
    index = _record(0, topics, bytes(references)+labels, previous=0, following=0)
    records = []
    for i, (topic, body) in enumerate(zip(topics, bodies)):
        records.append(_record(1, topic["lines"], body, root, i,
                               offsets[i-1] if i else NO_OFFSET,
                               offsets[i+1] if i+1 < len(topics) else NO_OFFSET))
    return header + menu + index + b"".join(records)


def xml_spans(element, style="", version=""):
    """Flatten editable mixed content while keeping DOS bold/underline styles."""
    result = [(element.text or "", style)]
    for child in element:
        if child.tag == "char":
            value = child.get("code", "")
            if not re.fullmatch(r"[0-9a-fA-F]{2}", value):
                raise ValueError("char code must contain two hexadecimal digits")
            result.append((chr(int(value, 16)), style))
        elif child.tag in ("b", "u", "code"):
            extra = "b" if child.tag == "b" else "u"
            result.extend(xml_spans(child, "".join(c for c in "bu" if c in style+extra), version))
        else:
            raise ValueError(f"unknown inline XML element {child.tag}")
        result.append((child.tail or "", style))
    return [(text.replace("{{version}}", version), fmt) for text, fmt in result]


def xml_text(element, version=""):
    return "".join(text for text, _ in xml_spans(element, version=version))


def prose_lines(element, version, bold=False):
    chars = [(c, fmt) for text, fmt in xml_spans(element, "b" if bold else "", version)
             for c in text]
    # XML editor indentation and paragraph line breaks are normal whitespace.
    normalized = []
    for c, fmt in chars:
        if c.isspace():
            if normalized and normalized[-1][0] != " ":
                normalized.append((" ", fmt))
        else:
            normalized.append((c, fmt))
    if normalized and normalized[-1][0] == " ":
        normalized.pop()
    plain = "".join(c for c, _ in normalized)
    wrapped = textwrap.wrap(plain, WIDTH, break_long_words=False, break_on_hyphens=False)
    result = []
    offset = 0
    for line in wrapped:
        if len(line) > WIDTH:
            raise ValueError(f"unbreakable text exceeds {WIDTH} columns: {line}")
        start = plain.index(line, offset)
        current = ""
        rendered = ""
        for c, fmt in normalized[start:start+len(line)]:
            for flag in "bu":
                if (flag in fmt) != (flag in current):
                    rendered += "^"+flag
            current = fmt
            rendered += "^^" if c == "^" else c
        for flag in "bu":
            if flag in current:
                rendered += "^"+flag
        result.append(rendered)
        offset = start+len(line)
    return result


def read_guide(path, version):
    root = ET.parse(path).getroot()
    if root.tag != "guide" or not root.get("language") or not root.get("codepage"):
        raise ValueError(f"{path}: expected guide language and codepage")
    topics = []
    for node in root:
        if node.tag == "credits":
            continue
        if node.tag != "topic" or node.find("title") is None or not node.get("id"):
            raise ValueError(f"{path}: expected topic id and title")
        title = xml_text(node.find("title"), version)
        layout = node.get("layout", "prose")
        lines = []
        if layout == "ng":
            for item in list(node)[1:]:
                if item.tag != "line":
                    raise ValueError("ng topics accept only line elements")
                lines.append(xml_text(item, version))
        elif layout == "prose":
            if len(title) > WIDTH:
                raise ValueError(f"{path}: index title exceeds {WIDTH} columns")
            lines = ["^b"+title.replace("^", "^^")+"^b", ""]
            title = title.replace("^", "^^")
            for item in list(node)[1:]:
                if item.tag in ("p", "heading"):
                    lines.extend(prose_lines(item, version, item.tag == "heading"))
                elif item.tag == "pre":
                    for line in xml_text(item, version).expandtabs(4).splitlines():
                        if len(line) > WIDTH:
                            raise ValueError(f"pre line exceeds {WIDTH} columns")
                        lines.append(line.replace("^", "^^"))
                else:
                    raise ValueError(f"unknown prose XML element {item.tag}")
                lines.append("")
            while lines and not lines[-1]:
                lines.pop()
        else:
            raise ValueError(f"unknown topic layout {layout}")
        topics.append({"id": node.get("id"), "title": title, "lines": lines})
    return {"language": root.attrib["language"], "codepage": root.attrib["codepage"], "topics": topics,
            "credits": [credit.text or "" for credit in root.findall("credits/credit")]}


def write_guide(document, output, language, original, digest):
    root = ET.Element("guide", language=language, codepage=document["codepage"],
                      original=original, **{"original-sha256": digest})
    credits = ET.SubElement(root, "credits")
    for credit in document["credits"]:
        ET.SubElement(credits, "credit").text = credit
    def content(parent, text):
        last = None
        for chunk in re.split(r"([\x01-\x08\x0b\x0c\x0e-\x1f])", text):
            if chunk and ord(chunk[0]) < 32 and len(chunk) == 1:
                last = ET.SubElement(parent, "char", code=f"{ord(chunk):02X}")
            elif last is None:
                parent.text = (parent.text or "")+chunk
            else:
                last.tail = (last.tail or "")+chunk
    for topic in document["topics"]:
        node = ET.SubElement(root, "topic", id=topic["id"], layout="ng")
        content(ET.SubElement(node, "title"), topic["title"])
        for line in topic["lines"]:
            content(ET.SubElement(node, "line"), line)
    saved = [(el, ET.tostring(el, encoding="unicode")) for el in root.iter()
             if el.tag in ("title", "line")]
    ET.indent(root, space="  ")
    for el, raw in saved:
        original_node = ET.fromstring(raw)
        el.text = original_node.text
        el[:] = list(original_node)
    # Preserve mixed-content whitespace in original DOS lines.
    output.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                      '<?xml-stylesheet type="text/css" href="../guide.css"?>\n'
                      '<!DOCTYPE guide SYSTEM "../guide.dtd">\n'
                      +ET.tostring(root, encoding="unicode")+"\n")


def context_map(definitions, contexts, topics):
    ids = {topic["id"]: i+1 for i, topic in enumerate(topics)}
    result = {}
    defined = re.findall(r"^(\w+_H)\s+EQU\s+(\d+)\b", definitions, re.MULTILINE)
    expected = {name for name, value in defined if int(value) != 255}
    if set(contexts) - expected:
        raise ValueError("unknown help contexts: " + ", ".join(sorted(set(contexts)-expected)))
    for name, value in defined:
        number = int(value)
        if number == 255:
            continue
        if name not in contexts:
            raise ValueError(f"missing context mapping for {name}")
        target = contexts[name]
        if target is not None and target not in ids:
            raise ValueError(f"context {name} references unknown topic {target}")
        index = ids[target] if target else 0
        if number in result and result[number] != index:
            raise ValueError(f"conflicting context number {number}")
        result[number] = index
    if not result or sorted(result) != list(range(max(result)+1)):
        raise ValueError("help context numbers must be contiguous")
    values = list(result[i] for i in range(len(result)))
    text = "; Generated by tools/hlp.py from help/project.xml; do not edit.\n"
    text += f"MaxHelp EQU {len(values)}\n"
    for i in range(0, len(values), 10):
        text += ("HelpMap DB " if not i else "        DB ")
        text += ", ".join(str(v) for v in values[i:i+10]) + "\n"
    return text.replace("\n", "\r\n").encode("ascii")


def build(project_path, output, version=None):
    project_path = Path(project_path)
    tree = ET.parse(project_path).getroot()
    if tree.tag != "help-project":
        raise ValueError("expected help-project XML root")
    project = dict(tree.attrib)
    project["languages"] = [dict(node.attrib) for node in tree.findall("languages/language")]
    project["contexts"] = {node.attrib["name"]: node.get("topic")
                           for node in tree.findall("contexts/context")}
    if len(project["contexts"]) != len(tree.findall("contexts/context")):
        raise ValueError("duplicate help context name")
    project["historical_topics"] = [node.attrib["id"] for node in tree.findall("historical/topic-ref")]
    if project.get("format") != "vc-norton-guides-v1":
        raise ValueError("unsupported help project format")
    root = project_path.parent
    definitions = (root / project["definitions"]).read_bytes().decode("latin1")
    if version is None:
        version = re.search(r"^VcVersion\s+EQU\s+'([^']+)'", definitions, re.MULTILINE)[1]
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    mapping = None
    layout = None
    reports = []
    for lang in project["languages"]:
        source = read_guide(root / lang["source"], version)
        if source["language"] != lang["code"]:
            raise ValueError("guide language does not match project language")
        topics = source["topics"]
        current_layout = [topic["id"] for topic in topics]
        if layout is not None and current_layout != layout:
            raise ValueError("language topic IDs/order differ")
        layout = current_layout
        for topic in topics:
            if topic["id"] in project.get("historical_topics", []):
                topic["title"] = "[4.05] " + topic["title"]
                annotated = ["^b" + lang["historical-notice"] + "^b", ""] + topic["lines"]
                if len(_encode_lines(annotated, source["codepage"])) <= MAX_PAYLOAD:
                    topic["lines"] = annotated
                else:
                    # Some original pages nearly fill the fixed DOS buffer.
                    topic["lines"] = ["^b[4.05]^b " + topic["lines"][0]] + topic["lines"][1:]
        current = context_map(definitions, project["contexts"], topics)
        if mapping is not None and current != mapping:
            raise ValueError("language topic order differs; context maps must be identical")
        mapping = current
        data = compile_guide(topics, source["codepage"], version, source["credits"])
        # Independent file traversal catches bad offsets before publication.
        decoded = decompile(data, source["codepage"])
        if [(t["title"], t["lines"]) for t in decoded["topics"]] != [
                (t["title"], t["lines"]) for t in topics]:
            raise ValueError("compiled help did not round-trip")
        (output / lang["output"]).write_bytes(data)
        reports.append({"language": lang["code"], "file": lang["output"],
                        "version": version, "topics": len(topics),
                        "sha256": hashlib.sha256(data).hexdigest()})
    if mapping is None:
        raise ValueError("project has no languages")
    (output / "VCHELPMAP.INC").write_bytes(mapping)
    manifest = ET.Element("help-build")
    for report in reports:
        ET.SubElement(manifest, "guide", {key: str(value) for key, value in report.items()})
    ET.indent(manifest)
    ET.ElementTree(manifest).write(output / "manifest.xml", encoding="utf-8", xml_declaration=True)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="decode an original VC HLP to editable UTF-8 XML")
    imp.add_argument("input", type=Path)
    imp.add_argument("output", type=Path)
    imp.add_argument("--codepage", required=True)
    imp.add_argument("--language", required=True)
    compile_cmd = sub.add_parser("build", help="build all project languages and the context map")
    compile_cmd.add_argument("--project", type=Path, default=Path("help/project.xml"))
    compile_cmd.add_argument("--output", type=Path, default=Path("build/help"))
    compile_cmd.add_argument("--version")
    args = parser.parse_args()
    try:
        if args.command == "import":
            data = args.input.read_bytes()
            document = decompile(data, args.codepage)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_guide(document, args.output, args.language, args.input.name, hashlib.sha256(data).hexdigest())
        else:
            for report in build(args.project, args.output, args.version):
                print(f"{report['file']}: {report['topics']} topics, version {report['version']}")
    except (ValueError, KeyError, UnicodeError, OSError, struct.error, ET.ParseError) as exc:
        parser.exit(1, f"hlp: {exc}\n")


if __name__ == "__main__":
    main()
