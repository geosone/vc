"""Stable archive records, including solid blocks and missing DOS metadata."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

EXE = Path(os.environ.get("VC7Z", "build/vc7z-host")).resolve()


class ArchiveBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def parse(self, listing, ok=True):
        p = self.root / "listing.txt"
        p.write_bytes(listing)
        result = subprocess.run([str(EXE), "--parse", str(p)], capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stderr)
        return result.stdout

    def test_solid_archive_optional_sizes_and_directories(self):
        listing = (b"Path = folder\r\nFolder = +\r\nSize = 0\r\nPacked Size = 0\r\n"
                   b"Modified = 2026-10-24 12:34:56.123\r\nAttributes = D\r\n\r\n"
                   b"Path = folder/one.txt\nSize = 123\nPacked Size = 50\n\n"
                   b"Path = folder/two words.txt\nSize = 456\nPacked Size = \n")
        out = self.parse(listing)
        self.assertEqual(out, b"VC7Z D...A 0 0 2026-10-24 12:34:56 folder\n"
                         b"VC7Z ....A 123 50 1980-01-01 00:00:00 folder\\one.txt\n"
                         b"VC7Z ....A 456 0 1980-01-01 00:00:00 folder\\two words.txt\n")

    def test_archive_header_is_not_a_member(self):
        out = self.parse(b"Path = a.7z\nType = 7z\nPhysical Size = 20\n\n"
                         b"Path = inside.txt\nSize = 0\nAttributes = RH\n\n")
        self.assertEqual(out, b"VC7Z .RH.A 0 0 1980-01-01 00:00:00 inside.txt\n")

    def test_invalid_sizes_controls_and_overlong_input(self):
        for listing in (b"Path = a\nSize = 4294967296\n", b"Path = a\nSize = -1\n",
                        b"Path = a\x1bb\n", b"Path = " + b"a" * 2000):
            self.parse(listing, ok=False)

    def test_empty_archive(self):
        self.assertEqual(self.parse(b""), b"")

    def test_pinned_dos_debug_prefix_does_not_hide_first_rar_member(self):
        p = self.root / "listing.txt"
        p.write_bytes(b"\r\nOpen: SOURCE.RARPath = directory/Path = real.txt\r\nSize = 22\r\n\r\n")
        result = subprocess.run([str(EXE), "--parse", str(p), "SOURCE.RAR"], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"directory\\Path = real.txt", result.stdout)

    def test_child_arguments_and_error_propagation(self):
        fake = self.root / "7za"
        fake.write_text("#!/bin/sh\n"
                        "test \"$1\" = l && test \"$2\" = -slt && test \"$5\" = -- || exit 8\n"
                        "printf 'Path = okay.txt\\nSize = 3\\n\\n'\n")
        fake.chmod(0o755)
        result = subprocess.run([str(EXE), 'archive with spaces;echo x.7z', str(fake)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"okay.txt", result.stdout)
        fake.write_text("#!/bin/sh\necho 'Path = partial.txt'\nexit 7\n")
        result = subprocess.run([str(EXE), "a.7z", str(fake)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
