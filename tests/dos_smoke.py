#!/usr/bin/env python3
"""Install and test the release in an isolated copy of a DOS disk image.

Example:
  python3 tests/dos_smoke.py --image /path/to/dos.img --offset 32256

Requires QEMU, mtools, a DOS-bootable raw hard disk, and `make disk`.
The original disk is only read. No DOS files are distributed with this test.
"""
import argparse
import json
import xml.etree.ElementTree as ET
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class QMP:
    def __init__(self, path, codepage="cp850"):
        self.codepage = codepage
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

    def chord(self, *keys):
        self.call("send-key", keys=[{"type": "qcode", "data": key} for key in keys])
        time.sleep(0.2)

    def screen(self, directory, name):
        self.call("human-monitor-command", command_line=
                  'pmemsave 0xb8000 4000 "' + str(directory / (name+".vram")) + '"')
        self.call("screendump", filename=str(directory / (name+".ppm")))
        chars = (directory / (name+".vram")).read_bytes()[::2]
        text = "\n".join(chars[i:i+80].decode(self.codepage) for i in range(0, 2000, 80))
        (directory / (name+".txt")).write_text(text)
        return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--offset", default=32256, type=int,
                        help="byte offset of the DOS FAT partition")
    parser.add_argument("--output", type=Path, default=ROOT / "build/dos-test")
    parser.add_argument("--full", action="store_true",
                        help="install directory release and test the downloaded packers")
    parser.add_argument("--licenses", action="store_true",
                        help="show all nine license dialogs and verify that declining aborts")
    parser.add_argument("--help-language", choices=("en", "de", "ru", "pl", "sk"), default="en",
                        help="exercise the generated guide in this DOS codepage")
    args = parser.parse_args()
    if args.licenses:
        args.full = True
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
    installer = "A:\\INSTALL /S"
    if args.full:
        output_disk = out / "destination.img"
        command("mformat", "-C", "-f", "1440", "-i", str(output_disk), "::")
        command("mmd", "-i", image, "::/VCDIST")
        for p in sorted((ROOT / "build/release").iterdir()):
            command("mcopy", "-s", "-o", "-i", image, str(p), "::/VCDIST/")
        installer = "C:\\VCDIST\\INSTALL /S"
    dosfile("CONFIG.SYS", "FILES=40\nBUFFERS=20\nLASTDRIVE=Z\nSHELL=C:\\COMMAND.COM C:\\ /P\n")
    help_names = {"en": "VC.HLP", "de": "VC-GER.HLP", "ru": "VCR.HLP",
                  "pl": "VC-PL.HLP", "sk": "VC-SK.HLP"}
    help_drive = "C:\\VCDIST" if args.full else "A:"
    select_help = f'COPY {help_drive}\\{help_names[args.help_language]} C:\\VC\\VC.HLP > NUL'
    autoexec = """@ECHO OFF
SET PATH=C:\\
SET TEMP=C:\\VCTEST
SET TZ=UTC0
A:\\INSTALL /S
IF ERRORLEVEL 1 ECHO INSTALL FAILED > C:\\VCTEST\\FAIL.TXT
SELECT_HELP
C:
CD \\VCTEST
CALL TEST.BAT
C:\\VC\\VC
C:\\QEXIT.COM
""".replace("A:\\INSTALL /S", installer).replace("SELECT_HELP", select_help)
    if args.licenses:
        autoexec = ("@ECHO OFF\nC:\\VCDIST\\INSTALL\n"
                    "IF EXIST C:\\VC\\VC.COM ECHO FILES COPIED > C:\\BAD.TXT\nC:\\QEXIT.COM\n")
    dosfile("AUTOEXEC.BAT", autoexec)
    dosfile("IN.LST", 'ONE.TXT\n"TWO WORD.TXT"\n', "::/VCTEST/")
    dosfile("BAD.LST", "BAD&NAME\n", "::/VCTEST/")
    batch = """@ECHO OFF
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
"""
    if args.full:
        dosfile("ORIG.TXT", "Archive test payload\n", "::/VCTEST/")
        command("mmd", "-i", image, "::/VCTEST/SUB", "::/VCTEST/AROUT",
                "::/VCTEST/ZOUT", "::/VCTEST/COUT", "::/VCTEST/ROUT", "::/VCTEST/SOUT",
                "::/VCTEST/LHOUT", "::/VCTEST/ARCOUT", "::/VCTEST/PKOUT",
                "::/VCTEST/A7", "::/VCTEST/AARC", "::/VCTEST/ALHA", "::/VCTEST/GUIOUT")
        dosfile("NEST.TXT", "Nested file\n", "::/VCTEST/SUB/")
        sample = out / "RAR5.RAR"
        command("rar", "a", "-ma5", str(sample), str(out / "ORIG.TXT"))
        command("mcopy", "-o", "-i", image, str(sample), "::/VCTEST/")
        checks = [
            ('ARJ a -y ATEST.ARJ ORIG.TXT', 'ARJA.TXT'),
            ('ARJ t ATEST.ARJ', 'ARJT.TXT'),
            ('ARJ x -y ATEST.ARJ AROUT\\', 'ARJX.TXT'),
            ('ZIP -9 ZTEST.ZIP ORIG.TXT', 'ZIPA.TXT'),
            ('UNZIP -t ZTEST.ZIP', 'ZIPT.TXT'),
            ('UNZIP ZTEST.ZIP -d ZOUT', 'ZIPX.TXT'),
            ('ACE a -y CTEST.ACE ORIG.TXT', 'ACEA.TXT'),
            ('ACE t CTEST.ACE', 'ACET.TXT'),
            ('ACE x -y CTEST.ACE COUT\\', 'ACEX.TXT'),
            ('RAR a -y RTEST.RAR ORIG.TXT', 'RARA.TXT'),
            ('UNRAR t RTEST.RAR', 'RART.TXT'),
            ('UNRAR x -y RTEST.RAR ROUT\\', 'RARX.TXT'),
            ('7ZA i', '7ZI.TXT'),
            ('7ZA a -t7z -mx=1 -md=1m -mmt=off STEST.7Z ORIG.TXT SUB', '7ZA.TXT'),
            ('7ZA t STEST.7Z', '7ZT.TXT'),
            ('VC7Z x STEST.7Z SOUT', '7ZX.TXT'),
            ('VC7Z x STEST.7Z A:\\', '7ZXDRV.TXT'),
            ('VC7Z STEST.7Z', '7ZLIST.TXT'),
            ('7ZA t RAR5.RAR', 'RAR5T.TXT'),
            ('VC7Z RAR5.RAR', 'RAR5L.TXT'),
            ('LHA a LTEST.LZH ORIG.TXT', 'LHAA.TXT'),
            ('LHA v LTEST.LZH', 'LHAL.TXT'),
            ('LHA t LTEST.LZH', 'LHAT.TXT'),
            ('LHA x LTEST.LZH LHOUT\\', 'LHAX.TXT'),
            ('ARC a ATEST.ARC ORIG.TXT', 'ARCA.TXT'),
            ('ARC v ATEST.ARC', 'ARCL.TXT'),
            ('ARC t ATEST.ARC', 'ARCT.TXT'),
            ('PKXARC ATEST.ARC ARCOUT\\', 'ARCX.TXT'),
            ('PKARC a PTEST.ARC ORIG.TXT', 'PKARCA.TXT'),
            ('PKXARC -t PTEST.ARC', 'PKARCT.TXT'),
            ('PKZIP -ex PTEST.ZIP ORIG.TXT', 'PKZIPA.TXT'),
            ('PKUNZIP -t PTEST.ZIP', 'PKZIPT.TXT'),
            ('PKUNZIP -d PTEST.ZIP PKOUT\\', 'PKZIPX.TXT'),
            ('7ZA a -ttar STEST.TAR ORIG.TXT SUB', 'TARA.TXT'),
            ('7ZA t STEST.TAR', 'TART.TXT'),
            ('7ZA a -tgzip STEST.GZ ORIG.TXT', 'GZA.TXT'),
            ('7ZA t STEST.GZ', 'GZT.TXT'),
            ('7ZA a -tbzip2 -mx=1 STEST.BZ2 ORIG.TXT', 'BZ2A.TXT'),
            ('7ZA t STEST.BZ2', 'BZ2T.TXT'),
            ('7ZA a -txz -mx=1 STEST.XZ ORIG.TXT', 'XZA.TXT'),
            ('7ZA t STEST.XZ', 'XZT.TXT'),
            ('7ZA a -twim STEST.WIM ORIG.TXT', 'WIMA.TXT'),
            ('7ZA t STEST.WIM', 'WIMT.TXT'),
        ]
        for cmd, logname in checks:
            exe, tail = cmd.split(" ", 1)
            batch += (f'C:\\VC\\{exe} {tail} > {logname}\n'
                      f'IF ERRORLEVEL 1 ECHO {logname} FAILED >> FAIL.TXT\n')
        batch += "COPY STEST.7Z A7\\ONLY.7Z > NUL\n"
        batch += "COPY ATEST.ARC AARC\\ONLY.ARC > NUL\n"
        batch += "COPY LTEST.LZH ALHA\\ONLY.LZH > NUL\n"
    batch += "ECHO DONE > DONE.TXT\n"
    dosfile("TEST.BAT", batch, "::/VCTEST/")
    dosfile("VC.MNU", """T: Helper home macro
    "!$VCTOOLS.EXE" type C:\\VCTEST\\SAMPLE.ZIP > HOME.TXT
""", "::/VCTEST/HOMECHK/")
    with zipfile.ZipFile(out / "SAMPLE.ZIP", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("long name.txt", b"example" * 10)
        z.comment = b"x" * 1022
    command("mcopy", "-o", "-i", image, str(out / "SAMPLE.ZIP"), "::/VCTEST/")
    if not args.full:
        core_floppy = out / "install.img"
        shutil.copyfile(ROOT / "build/vc49910a.img", core_floppy)
    sock = out / "qmp.sock"
    sock.unlink(missing_ok=True)
    env = dict(os.environ, SDL_AUDIODRIVER="dummy")
    with (out / "qemu.log").open("wb") as log:
        proc = subprocess.Popen([
            "qemu-system-i386", "-machine", "pc", "-accel", "tcg", "-cpu", "486",
            "-m", "64", "-display", "none", "-monitor", "none", "-serial", "none",
            "-drive", "if=ide,index=0,format=raw,file=" + str(disk),
            "-drive", "if=floppy,index=0,format=raw,file=" +
            str(output_disk if args.full else core_floppy),
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
            codepage = {"en": "cp437", "de": "cp850", "ru": "cp866", "pl": "cp852", "sk": "cp852"}[args.help_language]
            qmp = QMP(sock, codepage)
            if args.licenses:
                deadline = time.monotonic() + 30
                while "Welcome" not in qmp.screen(out, "welcome"):
                    if time.monotonic() > deadline:
                        raise RuntimeError("installer welcome dialog not reached")
                    time.sleep(0.5)
                qmp.key("ret")
                titles = ["Volkov Commander", "ARJ Open-Source", "Info-ZIP Zip / UnZip",
                          "ACE 1.2b shareware", "RAR 2.06 shareware", "UnRAR",
                          "Retro7Zip / 7-Zip", "LHA", "PKZIP / PKARC / ARC"]
                for i, title in enumerate(titles, 1):
                    deadline = time.monotonic() + 10
                    while True:
                        screen = qmp.screen(out, f"license-{i}")
                        if title in screen and "accept" in screen.lower():
                            break
                        if time.monotonic() > deadline:
                            raise RuntimeError("license not shown: " + title)
                        time.sleep(0.3)
                    if i == len(titles):
                        qmp.key("d")
                    else:
                        qmp.key("i")
                time.sleep(0.5)
                qmp.screen(out, "declined")
                qmp.key("ret")
                proc.wait(timeout=10)
                check = subprocess.run(["mdir", "-i", image, "::/VC/VC.COM"], capture_output=True)
                assert check.returncode != 0, "files copied despite declined license"
                print("PASS: all nine licenses displayed; decline prevents installation")
                print("Results:", out)
                return
            deadline = time.monotonic() + (120 if args.full else 50)
            while True:
                screen = qmp.screen(out, "startup")
                if "Volkov Commander" in screen and "SAMPLE" in screen.upper():
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("DOS tests did not reach VC; see startup.txt")
                time.sleep(1)
            titles = {
                "en": ("Current version and new features", "User menus and new macros"),
                "de": ("Aktuelle Version und Neuerungen", "Benutzermenüs und neue Makros"),
                "ru": ("Версия и новые функции", "Меню и новые макросы"),
                "pl": ("Wersja i nowe funkcje", "Menu i nowe makra"),
                "sk": ("Verzia a nové funkcie", "Menu a nové makrá")}
            release_title, menu_title = titles[args.help_language]
            qmp.key("f1")
            time.sleep(0.5)
            index_screen = qmp.screen(out, "help-index")
            assert release_title in index_screen, index_screen
            assert "Retro7Zip" in index_screen, index_screen
            qmp.key("ret")
            time.sleep(0.5)
            topic_screen = qmp.screen(out, "help-release")
            assert release_title in topic_screen, topic_screen
            assert "4.99.10" in topic_screen, topic_screen
            qmp.key("ret")
            time.sleep(0.5)
            assert menu_title in qmp.screen(out, "help-next")
            qmp.key("esc")
            qmp.key("f2", "f3", "f2", "f1")
            time.sleep(0.5)
            source = ET.parse(ROOT / f"help/src/{args.help_language}.xml").getroot()
            user_title = source.find("topic[@id='legacy_17']/title").text.strip()
            assert user_title in qmp.screen(out, "help-menu-context")
            qmp.key("esc", "esc")
            qmp.key("down", "f5", "f1")
            time.sleep(0.5)
            source = ET.parse(ROOT / f"help/src/{args.help_language}.xml").getroot()
            copy_title = source.find("topic[@id='legacy_20']/title").text.strip()
            assert copy_title in qmp.screen(out, "help-copy-context")
            qmp.key("esc", "esc", "home")
            qmp.key("f9", "o", "g", "f1")
            time.sleep(0.5)
            general_title = source.find("topic[@id='legacy_40']/title").text.strip()
            assert general_title in qmp.screen(out, "help-general-context")
            qmp.key("esc", "esc")
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
            if args.full:
                qmp.text("cd c:\\vctest\\a7")
                qmp.key("ret")
                time.sleep(0.5)
                qmp.key("down", "ret")
                time.sleep(3)
                archive_screen = qmp.screen(out, "7z-panel")
                assert "ORIG" in archive_screen.upper(), archive_screen
                assert "SUB" in archive_screen.upper(), archive_screen
                qmp.key("down", "f5")
                time.sleep(0.5)
                qmp.chord("ctrl", "y")
                qmp.text("c:\\vctest\\guiout\\")
                qmp.key("ret")
                time.sleep(3)
                qmp.screen(out, "7z-copy")
                # Return to the regular directory before testing the local menu.
                qmp.key("home", "ret")
                time.sleep(0.5)
                for folder, label in (("aarc", "arc-panel"), ("alha", "lha-panel")):
                    qmp.text("cd c:\\vctest\\" + folder)
                    qmp.key("ret")
                    time.sleep(0.5)
                    qmp.key("down", "ret")
                    time.sleep(2)
                    screen = qmp.screen(out, label)
                    assert "ORIG" in screen.upper(), screen
                    qmp.key("home", "ret")
                    time.sleep(0.5)
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
    installed_help = command("mtype", "-i", image, "::/VC/VC.HLP")
    assert installed_help == (ROOT / "build/help" / help_names[args.help_language]).read_bytes()
    print("PASS: generated F1 index, release, Next, user-menu, Copy and General contexts:", args.help_language)
    if args.full:
        for folder in ("AROUT", "ZOUT", "COUT", "ROUT", "SOUT", "LHOUT", "ARCOUT", "PKOUT"):
            assert b"Archive test payload" in read(folder + "/ORIG.TXT"), folder
        assert b"SUB\\NEST.TXT" in read("7ZLIST.TXT"), read("7ZLIST.TXT")
        assert b"VC7Z" in read("RAR5L.TXT"), read("RAR5L.TXT")
        assert b"Archive test payload" in read("GUIOUT/ORIG.TXT")
        cross_drive = command("mtype", "-i", str(output_disk), "::/ORIG.TXT")
        assert b"Archive test payload" in cross_drive
        print("PASS: ARJ, ZIP, ACE, RAR, LHA, ARC, PKARC and Retro7Zip pack/test/extract; RAR5 read")
    print("PASS: DOS install, lists, batch commands, detection, ZIP, hex, F2 menus and !$ macro")
    print("Results:", out)


if __name__ == "__main__":
    main()
