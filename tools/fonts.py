#!/usr/bin/env python3
"""Build complete DOS VGA fonts and a FONT-format CPI from readable sources.

Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
"""
import argparse
import hashlib
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET

try:
    from .assets import codepages
except ImportError:
    from assets import codepages

ROOT = Path(__file__).resolve().parents[1]
PAGES = (437, 850, 852, 866)
HEIGHTS = (16, 8)
# IBM display glyphs, rather than the Unicode meanings of control bytes.
CONTROLS = (0, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
            0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
            0x25ba, 0x25c4, 0x2195, 0x203c, 0xb6, 0xa7, 0x25ac, 0x21a8,
            0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc)
PINNED = {8: '03094f7fbab7085cf6a6b624cee61e47e71ce5d0c2f308c2f4436afdc17f776c',
          16: '2642c8b748fa81f24d76772d70c55faa720d98fadfec8133daf89136c5c8bfb1'}


def read_hex(path, height):
    result = {}
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if not re.fullmatch(r'[0-9A-Fa-f]{4,6}:[0-9A-Fa-f]+', line):
            raise ValueError(f'{path}:{number}: invalid HEX glyph')
        point, pixels = line.split(':')
        point, pixels = int(point, 16), bytes.fromhex(pixels)
        if point in result or point > 0x10ffff or 0xd800 <= point <= 0xdfff:
            raise ValueError(f'{path}:{number}: duplicate or invalid Unicode point')
        if len(pixels) not in (height, height * 2):
            raise ValueError(f'{path}:{number}: invalid glyph dimensions')
        # Double-width glyphs cannot be used in VGA cells. Keep as None so a
        # duplicate is still detected and a requested wide glyph fails loudly.
        result[point] = pixels if len(pixels) == height else None
    return result


def supplements(path):
    root = ET.parse(path).getroot()
    if root.tag != 'font-supplements' or root.get('license') != 'CC0-1.0':
        raise ValueError('invalid supplemental font source')
    result = {}
    for glyph in root:
        point = int(glyph.attrib['unicode'], 16)
        rows = [row.text or '' for row in glyph]
        if (glyph.tag != 'glyph' or point in result or len(rows) != 8 or
                any(row.tag != 'row' for row in glyph) or
                any(not re.fullmatch(r'[.#]{8}', row) for row in rows)):
            raise ValueError('invalid or duplicate supplemental 8x8 glyph')
        result[point] = bytes(int(row.replace('.', '0').replace('#', '1'), 2)
                              for row in rows)
    return result


def font(points, glyphs, height):
    display = list(points)
    display[:32] = CONTROLS
    display[0x7f] = 0x2302
    result = bytearray()
    for byte, point in enumerate(display):
        pixels = bytes(height) if point == 0 else glyphs.get(point)
        if pixels is None or len(pixels) != height:
            raise ValueError(f'missing {height}-pixel glyph U+{point:04X} at byte {byte:02X}')
        result.extend(pixels)
    return bytes(result)


def cpi(fonts):
    # MS-DOS FONT format, all pointers absolute and forward, total below 64K.
    result = bytearray(struct.pack('<8s8sHBIH', b'\xffFONT   ', bytes(8), 1, 1, 23, len(PAGES)))
    for index, page in enumerate(PAGES):
        data = b''.join(struct.pack('<BBBBH', h, 8, 0, 0, 256) + fonts[page, h]
                        for h in HEIGHTS)
        start = len(result)
        following = start + 28 + 6 + len(data) if index + 1 < len(PAGES) else 0
        result.extend(struct.pack('<HIH8sH6sI', 28, following, 1, b'EGA     ', page,
                                  bytes(6), start + 28))
        result.extend(struct.pack('<HHH', 1, len(HEIGHTS), len(data)))
        result.extend(data)
    result.extend(b'Unscii: Public Domain / CC0. VC supplements: CC0-1.0.\r\n')
    if len(result) >= 65536:
        raise ValueError('FONT-format CPI exceeds 64K')
    return bytes(result)


def names():
    return [f'FONTS/CP{p}.F{h:02}' for p in PAGES for h in HEIGHTS] + [
        'FONTS/VC.CPI', 'FONTS/UNSCII.TXT', 'FONTS/README.TXT']


def build(output):
    source = ROOT / 'assets/fonts'
    extra = supplements(source / 'supplements.xml')
    mappings = codepages(ROOT / 'assets/codepages.xml')
    fonts = {}
    for height in HEIGHTS:
        path = source / f'unscii-{height}.hex'
        if hashlib.sha256(path.read_bytes()).hexdigest() != PINNED[height]:
            raise ValueError(f'upstream source checksum mismatch: {path}')
        glyphs = read_hex(path, height)
        for point, pixels in extra.items():
            if glyphs.get(point) is not None:
                raise ValueError(f'supplement shadows upstream U+{point:04X}')
            glyphs[point] = pixels if height == 8 else bytes(v for v in pixels for _ in range(2))
        for page in PAGES:
            fonts[page, height] = font(mappings[f'cp{page}'], glyphs, height)
    products = {f'FONTS/CP{p}.F{h:02}': data for (p, h), data in fonts.items()}
    products['FONTS/VC.CPI'] = cpi(fonts)
    for origin, target in [('UNSCII.txt', 'UNSCII.TXT'), ('README.txt', 'README.TXT')]:
        products['FONTS/' + target] = (source / origin).read_text().replace('\n', '\r\n').encode('ascii')
    manifest = ET.Element('fonts', format='vga-unscii-v1')
    for height, digest in PINNED.items():
        ET.SubElement(manifest, 'source', path=f'assets/fonts/unscii-{height}.hex', sha256=digest)
    for path in [source / 'supplements.xml', ROOT / 'assets/codepages.xml']:
        ET.SubElement(manifest, 'source', path=str(path.relative_to(ROOT)),
                      sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    for name, data in products.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        ET.SubElement(manifest, 'file', path=name, size=str(len(data)), sha256=hashlib.sha256(data).hexdigest())
    ET.indent(manifest)
    ET.ElementTree(manifest).write(output / 'manifest.xml', encoding='utf-8', xml_declaration=True)
    print(f'Generated {len(fonts)} VGA fonts and VC.CPI in {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'build'])
    parser.add_argument('--output', type=Path, default=ROOT / 'build/fonts')
    args = parser.parse_args()
    if args.command == 'list':
        print(' '.join(names()))
    else:
        build(args.output)


if __name__ == '__main__':
    main()
