"""Independent checks of codepage coverage, source pixels and CPI layout."""
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from tools import fonts


class Fonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        fonts.build(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def raw(self, page, height):
        return (self.output / f'FONTS/CP{page}.F{height:02}').read_bytes()

    def test_complete_fonts_and_source_pixels(self):
        for height in (8, 16):
            source = fonts.read_hex(fonts.ROOT / f'assets/fonts/unscii-{height}.hex', height)
            for page in fonts.PAGES:
                data = self.raw(page, height)
                self.assertEqual(len(data), 256 * height)
                self.assertEqual(data[:height], bytes(height))
                for byte in range(32, 127):
                    self.assertEqual(data[byte*height:(byte+1)*height], source[byte])
                for byte in range(128, 256):
                    point = ord(bytes([byte]).decode(f'cp{page}'))
                    if point in source and source[point] is not None:
                        self.assertEqual(data[byte*height:(byte+1)*height], source[point])

    def test_codepages_are_distinct(self):
        # CP437 has a box-drawing glyph at D5, CP850 a dotless i.
        for height in (8, 16):
            self.assertNotEqual(self.raw(437, height)[0xd5*height:0xd6*height],
                                self.raw(850, height)[0xd5*height:0xd6*height])
        self.assertEqual(len({hashlib.sha256(self.raw(p, 8)).digest() for p in fonts.PAGES}), 4)

    def test_cpi_stream(self):
        data = (self.output / 'FONTS/VC.CPI').read_bytes()
        self.assertLess(len(data), 65536)
        self.assertEqual(data[:8], b'\xffFONT   ')
        self.assertEqual(struct.unpack_from('<HB', data, 16), (1, 1))
        position = struct.unpack_from('<I', data, 19)[0]
        count = struct.unpack_from('<H', data, position)[0]
        self.assertEqual(count, 4)
        position += 2
        pages = []
        for _ in range(count):
            size, following, device, name, page, reserved, info = struct.unpack_from('<HIH8sH6sI', data, position)
            self.assertEqual((size, device, name, reserved), (28, 1, b'EGA     ', bytes(6)))
            self.assertEqual(info, position + 28)
            version, number, length = struct.unpack_from('<HHH', data, info)
            self.assertEqual((version, number), (1, 2))
            end = info + 6 + length
            cursor = info + 6
            heights = []
            for _ in range(number):
                height, width, y, x, chars = struct.unpack_from('<BBBBH', data, cursor)
                self.assertEqual((width, y, x, chars), (8, 0, 0, 256))
                cursor += 6
                self.assertEqual(data[cursor:cursor+chars*height], self.raw(page, height))
                cursor += chars * height
                heights.append(height)
            self.assertEqual(heights, [16, 8])
            self.assertEqual(cursor, end)
            if following:
                self.assertEqual(following, end)
            position = following
            pages.append(page)
        self.assertEqual(position, 0)
        self.assertEqual(pages, [437, 850, 852, 866])

    def test_bad_sources_and_missing_glyph_fail(self):
        path = self.output / 'bad.hex'
        for content in ['0041:00\n', '0041:0000000000000000\n0041:0000000000000000\n',
                        'D800:0000000000000000\n', 'oops\n']:
            path.write_text(content)
            with self.assertRaises(ValueError):
                fonts.read_hex(path, 8)
        with self.assertRaisesRegex(ValueError, 'missing 8-pixel glyph'):
            fonts.font(list(range(256)), {}, 8)

    def test_supplements_are_readable_and_scaled(self):
        extra = fonts.supplements(fonts.ROOT / 'assets/fonts/supplements.xml')
        self.assertEqual(len(extra), 14)
        for page in fonts.PAGES:
            for byte in range(1, 256):
                point = (fonts.CONTROLS[byte] if byte < 32 else 0x2302 if byte == 127
                         else ord(bytes([byte]).decode(f'cp{page}')))
                if point in extra:
                    pixels = extra[point]
                    self.assertEqual(self.raw(page, 8)[byte*8:(byte+1)*8], pixels)
                    self.assertEqual(self.raw(page, 16)[byte*16:(byte+1)*16],
                                     bytes(v for v in pixels for _ in range(2)))


if __name__ == '__main__':
    unittest.main()
