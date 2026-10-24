#!/usr/bin/env python3
"""Probe the existing VC display with an externally supplied MAXTEXT driver.

This is a compatibility experiment, not a native MAXTEXT client in VC.
Requires a DOS image, built VC, QEMU, mtools and MAXTEXT.SYS/MAXTEXT.COM.
All changes are confined to a fresh copy of the supplied DOS image.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import time

from dos_smoke import QMP, ROOT


class Display(QMP):
    def screen(self, directory, name):
        bda = directory / (name + ".bda")
        self.call("human-monitor-command", command_line=f'pmemsave 0x400 256 "{bda}"')
        data = bda.read_bytes()
        columns = struct.unpack_from("<H", data, 0x4a)[0]
        rows = data[0x84] + 1
        page = struct.unpack_from("<H", data, 0x4e)[0]
        if not (40 <= columns <= 160 and 25 <= rows <= 100):
            raise ValueError(f"unexpected BDA geometry {columns}x{rows}")
        raw = directory / (name + ".vram")
        self.call("human-monitor-command", command_line=
                  f'pmemsave {0xb8000 + page} {columns*rows*2} "{raw}"')
        self.call("screendump", filename=str(directory / (name + ".ppm")))
        chars = raw.read_bytes()[::2]
        text = "\n".join(chars[i:i+columns].decode("cp437")
                         for i in range(0, len(chars), columns))
        (directory / (name + ".txt")).write_text(text)
        self.geometry = {"mode": data[0x49], "columns": columns, "rows": rows,
                         "font_height": struct.unpack_from("<H", data, 0x85)[0],
                         "page": data[0x62], "page_offset": page}
        return text


def command(*args):
    return subprocess.run(args, check=True, capture_output=True).stdout


def run_case(args, requested):
    out = args.output.resolve() / (str(requested) if requested else "no-driver")
    out.mkdir(parents=True, exist_ok=True)
    disk = out / "disk.img"
    if disk.exists():
        raise ValueError("use a fresh output directory to retain earlier results")
    shutil.copyfile(args.image, disk)
    image = str(disk) + "@@" + str(args.offset)
    command("mmd", "-i", image, "::/VC")
    for source in (ROOT / "build/VC.COM", ROOT / "build/VC.OVL",
                   ROOT / "build/help/VC.HLP"):
        command("mcopy", "-o", "-i", image, str(source), "::/VC/")

    def put(name, text):
        path = out / name
        path.write_bytes(text.replace("\n", "\r\n").encode("ascii"))
        command("mcopy", "-o", "-i", image, str(path), "::/")

    config = "FILES=40\nBUFFERS=20\nSHELL=C:\\COMMAND.COM C:\\ /P\n"
    before = ""
    if requested:
        for name in ("MAXTEXT.SYS", "MAXTEXT.COM"):
            command("mcopy", "-o", "-i", image, str(args.maxtext / name), "::/")
        config += "DEVICE=C:\\MAXTEXT.SYS\n"
        before = (f"C:\\MAXTEXT /MODE:80x{requested}\n"
                  "IF ERRORLEVEL 1 ECHO MODE FAILED > C:\\FAIL.TXT\n"
                  "C:\\MAXTEXT /STATUS > C:\\BEFORE.TXT\n")
        for rows in (25, 43, 50):
            put(f"TO{rows}.BAT", f"@ECHO OFF\nC:\\MAXTEXT /MODE:80x{rows}\n"
                f"IF ERRORLEVEL 1 ECHO SWITCH FAILED >> C:\\FAIL.TXT\n"
                f"C:\\MAXTEXT /STATUS > C:\\CHILD{rows}.TXT\n")
    put("CONFIG.SYS", config)
    put("AUTOEXEC.BAT", "@ECHO OFF\nSET PATH=C:\\\nSET TEMP=C:\\\n" + before +
        "CD \\VC\nC:\\VC\\VC\nECHO DONE > C:\\DONE.TXT\n" +
        ("C:\\MAXTEXT /STATUS > C:\\AFTER.TXT\n" if requested else "") +
        "C:\\QEXIT.COM\n")
    (out / "QEXIT.COM").write_bytes(bytes.fromhex("baf400b000eecd20"))
    command("mcopy", "-o", "-i", image, str(out / "QEXIT.COM"), "::/")
    sock = out / "qmp.sock"
    if requested:
        menu = ""
        for key, rows in enumerate((25, 43, 50), 1):
            menu += f"F{key}: MAXTEXT 80x{rows}\n    C:\\MAXTEXT /MODE:80x{rows}\n"
        put("VC.MNU", menu)
        command("mcopy", "-o", "-i", image, str(out / "VC.MNU"), "::/VC/")
    report = {"requested_rows": requested, "child_returns": [], "menu_returns": []}
    with (out / "qemu.log").open("wb") as log:
        proc = subprocess.Popen([
            "qemu-system-i386", "-machine", "pc", "-accel", "tcg", "-cpu", "486",
            "-m", "64", "-display", "none", "-monitor", "none", "-serial", "none",
            "-drive", "if=ide,index=0,format=raw,file=" + str(disk),
            "-boot", "c", "-nic", "none", "-no-reboot",
            "-device", "isa-debug-exit,iobase=0xf4,iosize=1",
            "-qmp", "unix:" + str(sock) + ",server=on,wait=off"], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 15
            while not sock.exists():
                if proc.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("QEMU did not start; see qemu.log")
                time.sleep(0.1)
            qmp = Display(sock)
            deadline = time.monotonic() + 45
            while True:
                screen = qmp.screen(out, "startup")
                if "Volkov Commander" in screen and "Help" in screen.splitlines()[-1]:
                    break
                if time.monotonic() > deadline:
                    raise RuntimeError("VC did not reach its panels")
                time.sleep(1)
            report["startup"] = dict(qmp.geometry)
            assert qmp.geometry["columns"] == 80
            assert qmp.geometry["rows"] == (requested or 25), report
            time.sleep(0.5)
            qmp.key("f1")
            time.sleep(0.5)
            assert "Current version and new features" in qmp.screen(out, "help-index")
            qmp.key("ret")
            time.sleep(0.5)
            assert "4.99.10" in qmp.screen(out, "help-topic")
            qmp.key("esc")
            qmp.key("f9", "o", "g", "f1")
            time.sleep(0.5)
            assert "General options" in qmp.screen(out, "help-general")
            qmp.key("esc", "esc")
            if requested:
                for rows in (25, 43, 50):
                    qmp.text(f"c:\\to{rows}")
                    qmp.key("ret")
                    time.sleep(2)
                    screen = qmp.screen(out, f"after-child-{rows}")
                    assert "Help" in screen.splitlines()[-1], screen
                    report["child_returns"].append({"child_requested": rows, **qmp.geometry})
                for key, rows in enumerate((25, 43, 50), 1):
                    qmp.key("f2", f"f{key}")
                    time.sleep(2)
                    screen = qmp.screen(out, f"after-menu-{rows}")
                    assert "Help" in screen.splitlines()[-1], screen
                    assert qmp.geometry["rows"] == rows, qmp.geometry
                    report["menu_returns"].append({"menu_requested": rows, **qmp.geometry})
            qmp.key("f10", "ret")
            proc.wait(timeout=15)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
    assert b"DONE" in command("mtype", "-i", image, "::/DONE.TXT")
    names = command("mdir", "-b", "-i", image, "::/")
    if b"FAIL.TXT" in names.upper():
        assert not command("mtype", "-i", image, "::/FAIL.TXT").strip()
    if requested:
        for name in ["BEFORE.TXT", "AFTER.TXT"] + [f"CHILD{r}.TXT" for r in (25, 43, 50)]:
            (out / name).write_bytes(command("mtype", "-i", image, "::/" + name))
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--offset", default=32256, type=int)
    parser.add_argument("--maxtext", required=True, type=Path,
                        help="external directory containing MAXTEXT.SYS and MAXTEXT.COM")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows", type=int, nargs="+", choices=(0, 25, 43, 50),
                        default=(0, 25, 43, 50), help="boot cases; 0 means no driver")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    binaries = [ROOT / "build/VC.COM", ROOT / "build/VC.OVL"]
    binaries += [args.maxtext / name for name in ("MAXTEXT.SYS", "MAXTEXT.COM")]
    (args.output / "inputs.sha256").write_text("".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path) + "\n"
        for path in binaries))
    for requested in args.rows:
        run_case(args, requested or None)


if __name__ == "__main__":
    main()
