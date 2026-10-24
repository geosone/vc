#!/usr/bin/env python3
"""Install and test the release in an isolated copy of a DOS disk image.

Example:
  python3 tests/dos_smoke.py --image /path/to/dos.img --offset 32256

Requires QEMU, mtools, a DOS-bootable raw hard disk, and `make disk`.
The original disk is only read. No DOS files are distributed with this test.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class QMP:
    def __init__(self, path):
        self.sock = socket.socket(socket.AF_UNIX)
        self.sock.settimeout(5)
        self.sock.connect(str(path))
        self.file = self.sock.makefile("rwb", buffering=0)
        self.file.readline()
        self.call("qmp_capabilities")

    def call(self, command, **arguments):
        arguments = {k.replace("_", "-"): v for k, v in arguments.items()}
        self.file.write(json.dumps({"execute": command, "arguments": arguments}).encode() + b"\n")
        while True:
            result = json.loads(self.file.readline())
            if "error" in result:
                raise RuntimeError(result)
            if "return" in result:
                return result["return"]

    def key(self, *keys):
        for key in keys:
            self.call("send-key", keys=[{"type": "qcode", "data": key}])
            time.sleep(0.15)

    def text(self, text):
        for c in text.lower():
            if c == ':':
                self.call("send-key", keys=[{"type": "qcode", "data": "shift"},
                                            {"type": "qcode", "data": "semicolon"}])
                time.sleep(0.15)
            else:
                self.key({" ": "spc", "\\": "backslash", ".": "dot"}.get(c, c))

    def screen(self, directory, name):
        self.call("human-monitor-command", command_line=
                  'pmemsave 0xb8000 4000 "' + str(directory / (name+".vram")) + '"')
        self.call("screendump", filename=str(directory / (name+".ppm")))
        chars = (directory / (name+".vram")).read_bytes()[::2]
        text = "\n".join(chars[i:i+80].decode("cp850") for i in range(0, 2000, 80))
        (directory / (name+".txt")).write_text(text)
        return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--offset", default=32256, type=int,
                        help="byte offset of the DOS FAT partition")
    parser.add_argument("--output", type=Path, default=ROOT / "build/dos-test")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    disk = out / "disk.img"
    if disk.exists():
        parser.error("use a fresh --output directory (to retain previous results)")
    shutil.copyfile(args.image, disk)
    image = str(disk) + "@@" + str(args.offset)

    def command(*cmd):
        return subprocess.run(cmd, check=True, capture_output=True).stdout

    def dosfile(name, content, destination="::/"):
        p = out / name
        p.write_bytes(content.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii"))
        command("mcopy", "-o", "-i", image, str(p), destination)

    def read(name):
        return command("mtype", "-i", image, "::/VCTEST/" + name).replace(b"\r\n", b"\n")

    command("mmd", "-i", image, "::/VCTEST", "::/VCTEST/HOMECHK")
    (out / "QEXIT.COM").write_bytes(bytes.fromhex("baf400b000eecd20"))
    command("mcopy", "-o", "-i", image, str(out / "QEXIT.COM"), "::/")
    dosfile("CONFIG.SYS", "FILES=40\nBUFFERS=20\nLASTDRIVE=Z\nSHELL=C:\\COMMAND.COM C:\\ /P\n")
    dosfile("AUTOEXEC.BAT", """@ECHO OFF
SET PATH=C:\\
SET TEMP=C:\\VCTEST
A:\\INSTALL /S
IF ERRORLEVEL 1 ECHO INSTALL FAILED > C:\\VCTEST\\FAIL.TXT
C:
CD \\VCTEST
CALL TEST.BAT
C:\\VC\\VC
C:\\QEXIT.COM
""")
    dosfile("IN.LST", 'ONE.TXT\n"TWO WORD.TXT"\n', "::/VCTEST/")
    dosfile("BAD.LST", "BAD&NAME\n", "::/VCTEST/")
    dosfile("TEST.BAT", """@ECHO OFF
C:\\VC\\VCTOOLS list IN.LST PRE: :END > LIST.TXT
IF ERRORLEVEL 1 ECHO LIST FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS list IN.LST --full > FULL.TXT
IF ERRORLEVEL 1 ECHO FULL FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS run IN.LST "ECHO {}" --dry-run > DRY.TXT
IF ERRORLEVEL 1 ECHO DRY FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS run IN.LST "ECHO {} >> RUN.TXT" > CMD.TXT
IF ERRORLEVEL 1 ECHO RUN FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS run BAD.LST "ECHO {}" --dry-run > BAD.TXT
IF NOT ERRORLEVEL 1 ECHO UNSAFE NAME ACCEPTED >> FAIL.TXT
C:\\VC\\VCTOOLS type SAMPLE.ZIP > TYPE.TXT
IF ERRORLEVEL 1 ECHO TYPE FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS zip SAMPLE.ZIP > ZIP.TXT
IF ERRORLEVEL 1 ECHO ZIP FAILED >> FAIL.TXT
C:\\VC\\VCTOOLS hex SAMPLE.ZIP 0 4 > HEX.TXT
IF ERRORLEVEL 1 ECHO HEX FAILED >> FAIL.TXT
ECHO DONE > DONE.TXT
""", "::/VCTEST/")
    dosfile("VC.MNU", """T: Helper home macro
    "!$VCTOOLS.EXE" type C:\\VCTEST\\SAMPLE.ZIP > HOME.TXT
""", "::/VCTEST/HOMECHK/")
    with zipfile.ZipFile(out / "SAMPLE.ZIP", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("long name.txt", b"example" * 10)
        z.comment = b"x" * 1022
    command("mcopy", "-o", "-i", image, str(out / "SAMPLE.ZIP"), "::/VCTEST/")
    sock = out / "qmp.sock"
    env = dict(os.environ, SDL_AUDIODRIVER="dummy")
    with (out / "qemu.log").open("wb") as log:
        proc = subprocess.Popen([
            "qemu-system-i386", "-machine", "pc", "-accel", "tcg", "-cpu", "486",
            "-m", "32", "-display", "none", "-monitor", "none", "-serial", "none",
            "-drive", "if=ide,index=0,format=raw,file=" + str(disk),
            "-drive", "if=floppy,index=0,format=raw,readonly=on,file=" + str(ROOT / "build/vc49910a.img"),
            "-boot", "c", "-nic", "none", "-no-reboot",
            "-device", "isa-debug-exit,iobase=0xf4,iosize=1",
            "-qmp", "unix:" + str(sock) + ",server=on,wait=off"],
            stdout=log, stderr=log, env=env)
        try:
            deadline = time.monotonic() + 10
            while not sock.exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("QEMU did not start; see qemu.log")
                time.sleep(0.1)
            qmp = QMP(sock)
            deadline = time.monotonic() + 50
            while True:
                screen = qmp.screen(out, "startup")
                if "Volkov Commander" in screen and "SAMPLE" in screen.upper():
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("DOS tests did not reach VC; see startup.txt")
                time.sleep(1)
            qmp.key("f2")
            time.sleep(0.5)
            assert "Erweiterungen" in qmp.screen(out, "main-menu")
            qmp.key("f3")
            time.sleep(0.5)
            assert "ARJ-Archive" in qmp.screen(out, "addons-menu")
            qmp.key("f2")
            time.sleep(0.5)
            assert "ARJ-Archiv pruefen" in qmp.screen(out, "arj-menu")
            qmp.key("esc")
            qmp.text("cd c:\\vctest\\homechk")
            qmp.key("ret")
            time.sleep(0.5)
            qmp.key("f2", "t")
            time.sleep(1)
            qmp.screen(out, "home-macro")
            # External commands may wait for a key before restoring panels.
            qmp.key("esc")
            qmp.key("f10", "ret")
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)

    assert b"DONE" in read("DONE.TXT")
    # COMMAND.COM may create a redirection target even when IF is false.
    assert not read("FAIL.TXT").strip(), read("FAIL.TXT")
    assert read("LIST.TXT") == b"PRE:ONE.TXT:END\nPRE:TWO WORD.TXT:END\n"
    assert b"C:\\VCTEST\\ONE.TXT" in read("FULL.TXT")
    assert b'ECHO "TWO WORD.TXT"' in read("DRY.TXT")
    assert b"ONE.TXT" in read("RUN.TXT") and b"TWO WORD.TXT" in read("RUN.TXT")
    assert b"ZIP archive" in read("TYPE.TXT")
    assert b"long name.txt" in read("ZIP.TXT")
    assert b"50 4B 03 04" in read("HEX.TXT")
    home = command("mtype", "-i", image, "::/VCTEST/HOMECHK/HOME.TXT")
    assert b"ZIP archive" in home, home
    print("PASS: DOS install, lists, batch commands, detection, ZIP, hex, F2 menus and !$ macro")
    print("Results:", out)


if __name__ == "__main__":
    main()
