#!/usr/bin/env python3
"""Generate VC translation tables and its Windows icon from XML/SVG sources.

Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
No binary input, downloaded packages or third-party Python modules required.
"""
import argparse
import hashlib
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def output_name(value):
    if not re.fullmatch(r"CP\d{3}/[A-Z0-9]{1,8}\.TBL", value):
        raise ValueError(f"invalid DOS table output path: {value}")
    return value


def unicode_point(value):
    if not re.fullmatch(r"[0-9A-F]{4,6}", value):
        raise ValueError("expected a hexadecimal Unicode codepoint")
    point = int(value, 16)
    if point > 0x10ffff or 0xd800 <= point <= 0xdfff:
        raise ValueError("invalid Unicode scalar value")
    return point


def codepages(path):
    root = ET.parse(path).getroot()
    if root.tag != "codepages" or root.get("format") != "unicode-repertoires-v1":
        raise ValueError("unsupported Unicode repertoire source")
    result = {}
    for node in root:
        name = node.attrib["id"]
        if node.tag != "codepage" or name in result:
            raise ValueError("invalid or duplicate codepage definition")
        if bool(node.get("codec")) == bool(node.get("base")):
            raise ValueError("codepage needs exactly one codec or base")
        if node.get("codec"):
            values = []
            for byte in range(256):
                try:
                    values.append(ord(bytes([byte]).decode(node.get("codec"))))
                except UnicodeDecodeError:
                    values.append(None)
        else:
            if node.get("base") not in result:
                raise ValueError("base codepage must be defined first")
            values = list(result[node.get("base")])
        seen = set()
        for char in node:
            byte = int(char.attrib["byte"], 16)
            if char.tag != "character" or not 128 <= byte <= 255 or byte in seen:
                raise ValueError("invalid or duplicate national character override")
            point = unicode_point(char.attrib["unicode"])
            if char.get("glyph") and char.get("glyph") != chr(point):
                raise ValueError("character glyph does not match its Unicode value")
            seen.add(byte)
            values[byte] = point
        result[name] = values
    return result


def inverse(points):
    result = {}
    for byte, point in enumerate(points):
        if point is not None:
            result.setdefault(point, byte)
    return result


def conversion(recipe, dos, external, profile):
    """Compute both directions through Unicode, independently of legacy TBLs."""
    out = {}
    contexts = {"to-external": (dos, external), "to-dos": (external, dos)}
    for direction, (source, target) in contexts.items():
        lookup = inverse(target)
        out[direction] = bytearray(lookup.get(point, 0) for point in source[128:])
    if profile == "standard":
        return bytes(out["to-external"] + out["to-dos"])
    seen = set()
    for rule in recipe:
        direction = rule.get("direction")
        if rule.tag == "passthrough":
            directions = contexts if direction == "both" else [direction]
            first, last = (int(rule.attrib[key], 16) for key in ("first", "last"))
            if not 128 <= first <= last <= 255 or any(d not in contexts for d in directions):
                raise ValueError("invalid legacy passthrough range")
            for d in directions:
                out[d][first-128:last-127] = bytes(range(first, last+1))
            continue
        if direction not in contexts:
            raise ValueError("invalid conversion direction")
        source, target = contexts[direction]
        lookup = inverse(target)
        if rule.tag == "undefined":
            byte = int(rule.attrib["byte"], 16)
            if not 128 <= byte <= 255 or source[byte] is not None:
                raise ValueError("undefined-slot rule requires an undefined input byte")
            inputs = [byte]
        elif rule.tag in ("replace", "omit"):
            point = unicode_point(rule.attrib["from"])
            inputs = [b for b in range(128, 256) if source[b] == point]
            if not inputs:
                raise ValueError("compatibility rule references a character absent from source")
        else:
            raise ValueError("unknown compatibility rule")
        value = 0
        if rule.tag != "omit":
            replacement = unicode_point(rule.attrib["to"])
            if replacement not in lookup:
                raise ValueError("replacement character absent from target codepage")
            value = lookup[replacement]
        for byte in inputs:
            if (direction, byte) in seen:
                raise ValueError("duplicate compatibility rule")
            seen.add((direction, byte))
            out[direction][byte-128] = value
    return bytes(out["to-external"] + out["to-dos"])


def compile_table(node, repertoires=None, profile="compat"):
    if profile not in ("compat", "standard"):
        raise ValueError("unknown charset generation profile")
    title = node.attrib["title"].encode("ascii")
    if not title or len(title) > 60 or any(c < 32 or c == 127 for c in title):
        raise ValueError("table title must fit the viewer's 60-character title field")
    kind = node.attrib["kind"]
    if kind == "unicode":
        if [child.tag for child in node] != ["unicode"]:
            raise ValueError("Unicode table needs one unicode element")
        definition = node.find("unicode")
        codec = definition.attrib["codec"]
        if codec not in ("cp437", "cp850", "cp852", "cp866"):
            raise ValueError("unsupported DOS Unicode codec")
        points = [ord(bytes([b]).decode(codec)) for b in range(128, 256)]
        overrides = set()
        for override in definition if profile == "compat" else ():
            if override.tag != "override":
                raise ValueError("unknown Unicode mapping element")
            key, value = override.attrib["byte"], override.attrib["codepoint"]
            if not re.fullmatch(r"[89A-F][0-9A-F]", key) or not re.fullmatch(r"[0-9A-F]{4}", value):
                raise ValueError("Unicode overrides need a high byte and a BMP codepoint")
            byte = int(key, 16)
            if byte in overrides:
                raise ValueError("duplicate Unicode override")
            overrides.add(byte)
            points[byte-128] = int(value, 16)
        payload = struct.pack("<128H", *points)
        flag = 1
    elif kind == "single-byte":
        if [child.tag for child in node] != ["conversion"]:
            raise ValueError("single-byte table needs one conversion recipe")
        if repertoires is None:
            repertoires = codepages(ROOT / "assets/codepages.xml")
        recipe = node.find("conversion")
        dos = repertoires[node.attrib["dos-codepage"]]
        external = repertoires[recipe.attrib["external"]]
        payload = conversion(recipe, dos, external, profile)
        flag = 0
    else:
        raise ValueError(f"unknown table kind: {kind}")
    return title + b"\r\n" + bytes([flag]) + payload


def compile_icon(root):
    ns = "{http://www.w3.org/2000/svg}"
    if root.tag != ns+"svg" or (root.get("width"), root.get("height"), root.get("viewBox")) != ("32", "32", "0 0 32 32"):
        raise ValueError("the VC icon SVG must have a 32x32 canvas")
    style = root.find(ns+"style")
    pattern = r"\.c([0-9A-F])\s*\{\s*fill:\s*#([0-9A-Fa-f]{6});?\s*\}"
    text = style.text if style is not None else ""
    entries = re.findall(pattern, text or "")
    if len(entries) != 16 or len(dict(entries)) != 16 or re.sub(pattern, "", text or "").strip():
        raise ValueError("SVG needs sixteen palette classes c0..cF with RGB fills")
    palette = bytearray()
    colors = dict(entries)
    for index in range(16):
        red, green, blue = bytes.fromhex(colors[f"{index:X}"])
        palette.extend((blue, green, red, 0))
    pixels = [[None]*32 for _ in range(32)]
    mask = [[0]*32 for _ in range(32)]
    for node in root:
        if node.tag in (ns+"title", ns+"desc", ns+"style"):
            continue
        if node.tag != ns+"rect" or set(node.attrib) - {"x", "y", "width", "height", "class", "opacity"}:
            raise ValueError("icon SVG supports only untransformed palette rectangles")
        color = node.get("class", "")
        opacity = node.get("opacity", "1")
        if not re.fullmatch(r"c[0-9A-F]", color) or opacity not in ("0", "1"):
            raise ValueError("icon rectangle needs a palette class and binary opacity")
        x, y, width, height = (int(node.attrib[key]) for key in ("x", "y", "width", "height"))
        if min(x, y) < 0 or min(width, height) < 1 or x+width > 32 or y+height > 32:
            raise ValueError("icon rectangle outside canvas")
        for row in range(y, y+height):
            for column in range(x, x+width):
                if pixels[row][column] is not None:
                    raise ValueError("pixel rectangles must tile the canvas without overlap")
                pixels[row][column] = int(color[1], 16)
                mask[row][column] = int(opacity == "0")
    if any(value is None for row in pixels for value in row):
        raise ValueError("icon rectangles must cover the complete canvas")
    pixel_bytes = b"".join(bytes(row[i]*16+row[i+1] for i in range(0, 32, 2))
                           for row in reversed(pixels))
    mask_bytes = b"".join(int("".join(str(bit) for bit in row), 2).to_bytes(4, "big")
                          for row in reversed(mask))
    bitmap = struct.pack("<IiiHHIIiiII", 40, 32, 64, 1, 4, 0,
                         len(pixel_bytes)+len(mask_bytes), 0, 0, 0, 0)
    bitmap += palette + pixel_bytes + mask_bytes
    # Preserve the original Win3.x directory fields (planes/bpp are zero).
    directory = struct.pack("<BBBBHHII", 32, 32, 16, 0, 0, 0, len(bitmap), 22)
    return struct.pack("<HHH", 0, 1, 1) + directory + bitmap


def sources(directory, profile="compat"):
    repertoires = codepages(directory / "codepages.xml")
    root = ET.parse(directory / "charsets.xml").getroot()
    if root.tag != "charsets" or root.get("format") != "vc-tbl-v2":
        raise ValueError("unsupported translation table source")
    result = {}
    for node in root:
        if node.tag != "table":
            raise ValueError("unknown charset source element")
        name = output_name(node.attrib["file"])
        if name in result:
            raise ValueError("duplicate output table path")
        result[name] = (compile_table(node, repertoires, profile), node.attrib["original-sha256"])
    icon = ET.parse(directory / "vc-icon.svg").getroot()
    result["VC.ICO"] = (compile_icon(icon), icon.attrib["data-original-sha256"])
    return result


def build(directory, output, profile="compat"):
    result = sources(directory, profile)
    manifest = ET.Element("assets-build", profile=profile)
    for name, (data, original) in sorted(result.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        ET.SubElement(manifest, "file", name=name, sha256=hashlib.sha256(data).hexdigest(),
                      **{"original-sha256": original})
    ET.indent(manifest)
    ET.ElementTree(manifest).write(output / "manifest.xml", encoding="utf-8", xml_declaration=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "list"))
    parser.add_argument("--sources", type=Path, default=ROOT / "assets")
    parser.add_argument("--output", type=Path, default=ROOT / "build/assets")
    parser.add_argument("--profile", choices=("compat", "standard"), default="compat")
    args = parser.parse_args()
    try:
        if args.command == "list":
            print(" ".join(sorted(sources(args.sources, args.profile))))
        else:
            result = build(args.sources, args.output, args.profile)
            print(f"Generated {len(result)-1} translation tables and VC.ICO from XML/SVG")
    except (ValueError, KeyError, LookupError, OSError, ET.ParseError, UnicodeError, struct.error) as exc:
        parser.exit(1, f"assets: {exc}\n")


if __name__ == "__main__":
    main()
