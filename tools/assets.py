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


def mapping(node):
    if node is None or len(node) != 8:
        raise ValueError("a byte mapping needs eight rows of sixteen values")
    result = bytearray()
    for first, row in zip(range(128, 256, 16), node):
        if row.tag != "row" or row.get("first") != f"{first:02X}":
            raise ValueError("byte mapping rows must cover 80..FF in order")
        values = (row.text or "").split()
        if len(values) != 16 or any(not re.fullmatch(r"[0-9A-F]{2}", v) for v in values):
            raise ValueError("each byte mapping row needs sixteen hexadecimal bytes")
        result.extend(int(v, 16) for v in values)
    return bytes(result)


def compile_table(node):
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
        for override in definition:
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
        if [child.tag for child in node] != ["to-external", "to-dos"]:
            raise ValueError("single-byte table needs both mapping directions")
        payload = mapping(node.find("to-external")) + mapping(node.find("to-dos"))
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


def sources(directory):
    root = ET.parse(directory / "charsets.xml").getroot()
    if root.tag != "charsets" or root.get("format") != "vc-tbl-v1":
        raise ValueError("unsupported translation table source")
    result = {}
    for node in root:
        if node.tag != "table":
            raise ValueError("unknown charset source element")
        name = output_name(node.attrib["file"])
        if name in result:
            raise ValueError("duplicate output table path")
        result[name] = (compile_table(node), node.attrib["original-sha256"])
    icon = ET.parse(directory / "vc-icon.svg").getroot()
    result["VC.ICO"] = (compile_icon(icon), icon.attrib["data-original-sha256"])
    return result


def build(directory, output):
    result = sources(directory)
    manifest = ET.Element("assets-build")
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
    args = parser.parse_args()
    try:
        if args.command == "list":
            print(" ".join(sorted(sources(args.sources))))
        else:
            result = build(args.sources, args.output)
            print(f"Generated {len(result)-1} translation tables and VC.ICO from XML/SVG")
    except (ValueError, KeyError, OSError, ET.ParseError, UnicodeError, struct.error) as exc:
        parser.exit(1, f"assets: {exc}\n")


if __name__ == "__main__":
    main()
