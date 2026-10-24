"""Exercise the helper through its public command line, using real files."""
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile

EXE = Path(os.environ.get("VCTOOLS", "build/vctools-host")).resolve()


class Helpers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.cwd = Path(self.temp.name)

    def call(self, *args, ok=True):
        p = subprocess.run([str(EXE), *map(str, args)], cwd=self.cwd,
                           capture_output=True)
        if ok:
            self.assertEqual(p.returncode, 0, p.stderr.decode(errors="replace"))
        else:
            self.assertNotEqual(p.returncode, 0, p.stdout)
        return p

    def write(self, name, data):
        p = self.cwd / name
        p.write_bytes(data)
        return p

    def archive(self, name="a.zip", comment=b""):
        p = self.cwd / name
        with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("folder/", b"")
            z.writestr("folder/hello world.txt", b"hello\n" * 30)
            z.writestr("empty.bin", b"")
            z.comment = comment
        return p

    def test_lists_crlf_quotes_prefix_suffix_full_paths(self):
        self.write("in.lst", b'ONE.TXT\r\n"two words.txt"\r\n\r\nLAST.BIN')
        self.assertEqual(self.call("list", "in.lst", "pre:", ":post").stdout,
                         b"pre:ONE.TXT:post\npre:two words.txt:post\npre:LAST.BIN:post\n")
        out = self.call("list", "in.lst", "--full").stdout.decode().splitlines()
        self.assertEqual(out, [str(self.cwd / n) for n in
                              ("ONE.TXT", "two words.txt", "LAST.BIN")])

    def test_overlong_list_is_an_error_not_a_partial_name(self):
        self.write("in.lst", b"X" * 2048 + b"\n")
        self.assertEqual(self.call("list", "in.lst", ok=False).stdout, b"")

    def test_run_dry_run_quotes_and_repeats_placeholders(self):
        self.write("in.lst", b'"two words.txt"\r\nONE.TXT\n')
        self.assertEqual(self.call("run", "in.lst", "echo {} {}", "--dry-run").stdout,
                         b'echo "two words.txt" "two words.txt"\necho "ONE.TXT" "ONE.TXT"\n')
        self.assertFalse((self.cwd / "side.txt").exists())

    def test_run_really_invokes_each_command(self):
        self.write("in.lst", b"one\ntwo words\n")
        self.call("run", "in.lst", "echo {} >> result.txt")
        self.assertEqual((self.cwd / "result.txt").read_text(), "one\ntwo words\n")

    def test_run_stops_after_error(self):
        self.write("in.lst", b"one\ntwo\n")
        p = self.call("run", "in.lst", "echo {} >> seen.txt; exit 7", ok=False)
        self.assertIn(b"remaining files", p.stderr)
        self.assertEqual((self.cwd / "seen.txt").read_text(), "one\n")

    def test_run_rejects_unsafe_names_long_commands_missing_placeholder(self):
        for name in (b"A&echo BAD", b"%PATH%", b'a"b', b"$(id)", b"A\x1bB"):
            self.write("in.lst", name + b"\n")
            self.call("run", "in.lst", "echo {}", "--dry-run", ok=False)
        self.write("in.lst", b"OK\n")
        self.call("run", "in.lst", "echo missing", ok=False)
        self.call("run", "in.lst", "echo " + "x" * 125 + " {}", ok=False)

    def test_identifies_content_despite_wrong_extension(self):
        cases = [(b"PK\x03\x04", b"ZIP"), (b"\x60\xea", b"ARJ"),
                 (b"Rar!\x1a\x07\x00", b"RAR"), (b"1234567**ACE**", b"ACE"),
                 (b"\x07\x00-lh5-", b"LHA"), (b"MZ\0", b"executable"),
                 (b"\x89PNG\r\n\x1a\n", b"PNG"), (b"%PDF-1.4", b"PDF"),
                 (b"hello\r\n", b"Text"), (b"\0\xff", b"Unknown"), (b"", b"Empty")]
        for data, expected in cases:
            with self.subTest(expected=expected):
                self.write("wrong.ext", data)
                self.assertIn(expected, self.call("type", "wrong.ext").stdout)

    def test_zip_lists_deflated_empty_and_long_names(self):
        p = self.archive()
        out = self.call("zip", p).stdout
        self.assertIn(b"folder/hello world.txt", out)
        self.assertIn(b"180", out)
        self.assertIn(b"3 entries", out)
        with zipfile.ZipFile(self.cwd / "empty.zip", "w"):
            pass
        self.assertIn(b"0 entries", self.call("zip", "empty.zip").stdout)

    def test_zip_large_comment_and_block_boundary_search(self):
        for size in (1001, 1021, 1022, 2048, 65535):
            with self.subTest(size=size):
                self.assertIn(b"3 entries", self.call("zip", self.archive(comment=b"x" * size)).stdout)

    def test_zip_self_extracting_prefix(self):
        p = self.archive()
        p.write_bytes(b"MZ" + bytes(510) + p.read_bytes())
        self.assertIn(b"3 entries", self.call("zip", p).stdout)

    def test_zip_malformed_and_unsupported(self):
        valid = self.archive().read_bytes()
        end = valid.rfind(b"PK\x05\x06")
        for data in (valid[:-1], valid[:10], b"not a zip",
                     valid[:end+4] + struct.pack("<H", 1) + valid[end+6:]):
            self.write("bad.zip", data)
            self.call("zip", "bad.zip", ok=False)
        data = bytearray(valid)
        data[end+10:end+12] = b"\xff\xff"
        self.write("zip64.zip", data)
        self.call("zip", "zip64.zip", ok=False)
        data = bytearray(valid)
        central = data.find(b"PK\x01\x02")
        data[central+28:central+30] = b"\xff\xff"
        self.write("overflow.zip", data)
        self.call("zip", "overflow.zip", ok=False)

    def test_zip_sanitizes_control_characters_in_names(self):
        with zipfile.ZipFile(self.cwd / "control.zip", "w") as z:
            z.writestr("bad\x1bname.txt", b"")
        out = self.call("zip", "control.zip").stdout
        self.assertIn(b"bad?name.txt", out)
        self.assertNotIn(b"\x1b", out)

    def test_hex_range_and_invalid_arguments(self):
        self.write("data.bin", bytes(range(32)))
        out = self.call("hex", "data.bin", "0x10", "4").stdout
        self.assertIn(b"00000010  10 11 12 13", out)
        self.assertEqual(len(out.splitlines()), 1)
        self.call("hex", "data.bin", "-1", ok=False)
        self.call("hex", "data.bin", "nonsense", ok=False)
        self.call("hex", "data.bin", "0", "-2", ok=False)
        self.assertEqual(self.call("hex", "data.bin", "0", "0").stdout, b"")

    def test_usage_missing_files_and_unknown_commands(self):
        self.call("--help")
        self.call("unknown", "file", ok=False)
        for command in ("list", "type", "zip", "hex"):
            self.call(command, "missing", ok=False)


if __name__ == "__main__":
    unittest.main()
