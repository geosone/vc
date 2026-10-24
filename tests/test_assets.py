"""Check generated legacy assets without keeping original binaries in Git."""
import copy
import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
from tools import assets

ROOT = Path(__file__).resolve().parents[1]


class AssetCompiler(unittest.TestCase):
    def test_outputs_match_the_verified_upstream_checksums(self):
        records = assets.sources(ROOT / 'assets')
        self.assertEqual(len(records), 16)
        for name, (data, original_hash) in records.items():
            with self.subTest(name=name):
                self.assertEqual(hashlib.sha256(data).hexdigest(), original_hash)

    def test_unicode_tables_preserve_documented_historical_variants(self):
        records = assets.sources(ROOT / 'assets')
        for cp, byte, expected in [('CP437', 0xE6, 0x03BC), ('CP850', 0xD5, 0x20AC),
                                   ('CP852', 0xAA, 0xFFFF), ('CP866', 0x80, 0x0410)]:
            data = records[f'{cp}/{cp}UNI.TBL'][0]
            title, body = data.split(b'\r\n', 1)
            self.assertEqual(body[0], 1)
            self.assertEqual(len(body), 257)
            self.assertEqual(struct.unpack_from('<H', body, 1+2*(byte-128))[0], expected)

    def test_single_byte_payload_has_both_mapping_directions(self):
        data = assets.sources(ROOT / 'assets')['CP866/CP1251.TBL'][0]
        body = data.split(b'\r\n', 1)[1]
        self.assertEqual(len(body), 257)
        self.assertEqual(body[0], 0)
        self.assertEqual(body[1], 0xC0)  # CP866 Cyrillic A -> Windows-1251
        self.assertEqual(body[129+0xC0-128], 0x80)  # Windows-1251 -> CP866

    def test_svg_produces_a_win3x_compatible_icon_with_transparency(self):
        svg = ET.parse(ROOT / 'assets/vc-icon.svg').getroot()
        data = assets.compile_icon(svg)
        self.assertEqual(struct.unpack_from('<HHH', data), (0, 1, 1))
        self.assertEqual(struct.unpack_from('<BBBBHHII', data, 6), (32, 32, 16, 0, 0, 0, 744, 22))
        self.assertEqual(struct.unpack_from('<IiiHH', data, 22), (40, 32, 64, 1, 4))
        self.assertEqual(len(data), 766)
        self.assertEqual(data[638:], bytes(128))  # Original icon is fully opaque.
        transparent = copy.deepcopy(svg)
        transparent.find('{http://www.w3.org/2000/svg}rect').set('opacity', '0')
        self.assertTrue(any(assets.compile_icon(transparent)[638:]))
        changed = copy.deepcopy(svg)
        rect = changed.find('{http://www.w3.org/2000/svg}rect')
        rect.set('x', '32')
        with self.assertRaisesRegex(ValueError, 'outside canvas'):
            assets.compile_icon(changed)

    def test_conversion_is_computed_from_repertoires_not_saved_byte_rows(self):
        node = ET.parse(ROOT / 'assets/charsets.xml').getroot().find("table[@file='CP866/CP1251.TBL']")
        self.assertEqual(assets.compile_table(node, profile='standard')[-256], 0xC0)
        changed = copy.deepcopy(node)
        recipe = changed.find('conversion')
        recipe.set('external', 'koi8_r')
        self.assertEqual(assets.compile_table(changed, profile='standard')[-256], 0xE1)
        self.assertIsNone(node.find('.//row'))

    def test_standard_profile_omits_legacy_approximations(self):
        standard = assets.sources(ROOT / 'assets', 'standard')
        compatible = assets.sources(ROOT / 'assets')
        # Copyright cannot be represented in CP866; the old approximation was c.
        position = 128 + 0xBF-128
        self.assertEqual(standard['CP866/KOI8R.TBL'][0][-256:][position], 0)
        self.assertEqual(compatible['CP866/KOI8R.TBL'][0][-256:][position], ord('c'))
        # Real CP850 has dotless i here; the legacy VC table had the Euro sign.
        value = struct.unpack_from('<H', standard['CP850/CP850UNI.TBL'][0][-256:], 2*(0xD5-128))[0]
        self.assertEqual(value, 0x0131)

    def test_national_encodings_have_explicit_unicode_repertoires(self):
        pages = assets.codepages(ROOT / 'assets/codepages.xml')
        self.assertEqual(pages['kamenicky'][0x80], ord('Č'))
        self.assertEqual(pages['mazovia'][0x86], ord('ą'))
        self.assertEqual(pages['cwi2'][0x93], ord('ő'))
        self.assertEqual(pages['cp1125'][0xF6], ord('І'))
        for page in ('kamenicky', 'mazovia', 'cwi2'):
            self.assertEqual(pages[page][0xC4], ord('─'))
        strict = assets.sources(ROOT / 'assets', 'standard')
        # The old KAMENICT file is a VC variant; the standard aliases agree.
        self.assertEqual(strict['CP852/KAMENICT.TBL'][0][-256:],
                         strict['CP852/CP895.TBL'][0][-256:])

    def test_rejects_unresolvable_or_duplicate_compatibility_rules(self):
        node = ET.parse(ROOT / 'assets/charsets.xml').getroot().find("table[@file='CP866/CP1251.TBL']")
        bad = copy.deepcopy(node)
        bad.find('conversion/replace').set('from', '10FFFF')
        with self.assertRaisesRegex(ValueError, 'absent from source'):
            assets.compile_table(bad)
        bad = copy.deepcopy(node)
        recipe = bad.find('conversion')
        recipe.append(copy.deepcopy(recipe.find('replace')))
        with self.assertRaisesRegex(ValueError, 'duplicate compatibility'):
            assets.compile_table(bad)
        with self.assertRaises(ValueError):
            assets.output_name('../VC.ICO')

    def test_build_creates_all_files_and_a_text_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            expected = assets.build(ROOT / 'assets', out)
            manifest = ET.parse(out / 'manifest.xml').getroot()
            self.assertEqual({node.get('name') for node in manifest}, set(expected))
            self.assertTrue((out / 'CP852/CP1250.TBL').is_file())
            self.assertTrue((out / 'VC.ICO').is_file())


if __name__ == '__main__':
    unittest.main()
