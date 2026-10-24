"""Pinned downloads, cache integrity and generated installer entries."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import packers


class Downloads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_pinned_manifest_contains_all_requested_tools(self):
        specs = packers.manifest(Path(__file__).resolve().parents[1] / "downloads.txt")
        self.assertEqual(set(specs), {"arj", "arjsrc", "zip", "unzip", "ace", "rar",
                                     "unrar", "retro7zip", "autoins", "os2icons", "os2icons2",
                                     "lha", "pkzip", "pkarc", "arc", "arcorig"})
        self.assertTrue(all(s[1].startswith("https://") for s in specs.values()))

    def test_download_cache_and_corrupt_cache_recovery(self):
        src = self.root / "original.bin"
        src.write_bytes(b"known binary contents")
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        spec = digest, src.as_uri(), "package.bin"
        cache = self.root / "cache"
        downloaded = packers.fetch(spec, cache)
        with patch("tools.packers.subprocess.run", side_effect=AssertionError("network used")):
            self.assertEqual(packers.fetch(spec, cache), downloaded)
        downloaded.write_bytes(b"corrupt")
        self.assertEqual(packers.fetch(spec, cache).read_bytes(), src.read_bytes())

    def test_bad_download_never_becomes_valid_cache(self):
        src = self.root / "wrong.bin"
        src.write_bytes(b"unexpected bytes")
        cache = self.root / "cache"
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            packers.fetch(("0" * 64, src.as_uri(), "package.bin"), cache)
        self.assertFalse((cache / "package.bin").exists())
        self.assertFalse(list(cache.glob("*.part")))

    def test_manifest_rejects_duplicate_and_invalid_names(self):
        p = self.root / "downloads.txt"
        for text in ("missing fields", "x " + "0" * 64 + " https://example.com ../escape",
                     ("x " + "0" * 64 + " https://example.com pkg\n") * 2):
            p.write_text(text)
            with self.assertRaises(ValueError):
                packers.manifest(p)

    def test_installer_includes_nested_docs_and_retains_language_choices(self):
        template = self.root / "INSTALL.INI"
        template.write_bytes(b"[Files]\r\n@de|VC-GER.HLP=VC.HLP\r\nVC.COM\r\n[Keep]\r\nVC.INI\r\n")
        result = packers.install_ini(template, {"ARJ.EXE", "PACKDOC/ARJ/SOURCE.TGZ"})
        self.assertIn(b"PACKDOC\\ARJ\\SOURCE.TGZ\r\n", result)
        self.assertIn(b"@de|VC-GER.HLP=VC.HLP\r\n", result)
        self.assertIn(b"[Keep]\r\nVC.INI", result)

    def test_every_license_is_selected_and_named(self):
        template = self.root / "INSTALL.INI"
        template.write_bytes(b"[Setup]\r\nLicense=Volkov Commander|LICENSE.TXT\r\n[Files]\r\nVC.COM\r\n")
        licenses = [("VC", "LICENSE.TXT"), ("ARJ", "PACKDOC/ARJ/COPYING.TXT")]
        result = packers.install_ini(template, {"ARJ.EXE"}, licenses)
        self.assertIn(b"License=1,2\r\n", result)
        self.assertIn(b"License1=VC|LICENSE.TXT\r\n", result)
        self.assertIn(b"License2=ARJ|PACKDOC\\ARJ\\COPYING.TXT\r\n", result)
        with self.assertRaises(ValueError):
            packers.install_ini(template, set(), licenses * 5)


if __name__ == "__main__":
    unittest.main()
