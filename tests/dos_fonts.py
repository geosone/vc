#!/usr/bin/env python3
"""Test all 256 VGA glyphs, geometry, ROM restore and errors in real DOS.

Only reads the supplied bootable image; creates a fresh disposable copy.
Requires make all, QEMU, mtools, OpenWatcom and optionally MAXTEXT binaries.
"""
import argparse
import json
import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import os
from dos_smoke import ROOT


def run(*args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, **kwargs).stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image', required=True, type=Path)
    ap.add_argument('--offset', type=int, default=32256)
    ap.add_argument('--maxtext', type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args = ap.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    disk = out / 'disk.img'
    shutil.copyfile(args.image, disk)
    image = str(disk) + '@@' + str(args.offset)
    watcom = Path(os.environ.get('WATCOM', '/opt/watcom'))
    env = dict(os.environ, WATCOM=str(watcom), INCLUDE=str(watcom / 'h'))
    env['PATH'] = str(watcom / 'binl64') + ':' + env['PATH']
    run(os.environ.get('WCL', str(watcom / 'binl64/wcl')), '-q', '-bt=dos', '-0', '-ms', '-os', '-w4', '-we',
        '-fe=' + str(out / 'PROBE.EXE'), '-fo=' + str(out / 'probe.obj'),
        str(ROOT / 'tests/dos/fontprobe.c'), env=env)
    run('mmd', '-i', image, '::/VC')
    for source in [out / 'PROBE.EXE', ROOT / 'build/VCFONT.EXE', ROOT / 'build/fonts/FONTS']:
        run('mcopy', '-s', '-o', '-i', image, str(source), '::/VC/')
    def put(name, content):
        path = out / name
        path.write_bytes(content.replace('\n', '\r\n').encode('ascii'))
        run('mcopy', '-o', '-i', image, str(path), '::/')
    config = 'FILES=40\nBUFFERS=20\nSHELL=C:\\COMMAND.COM C:\\ /P\n'
    if args.maxtext:
        config += 'DEVICE=C:\\MAXTEXT.SYS\n'
        for name in ('MAXTEXT.SYS', 'MAXTEXT.COM'):
            run('mcopy', '-o', '-i', image, str(args.maxtext / name), '::/')
    put('CONFIG.SYS', config)
    batch = '@ECHO OFF\nSET PATH=C:\\;C:\\VC\nCD \\\n'
    expected = []
    for height in (16, 8):
        if args.maxtext:
            batch += f'C:\\MAXTEXT /MODE:80x{25 if height == 16 else 50}\n'
        else:
            batch += f'C:\\VC\\PROBE b{height}\n'
        batch += f'C:\\VC\\PROBE R{height}.BIN\n'
        for page in (437, 850, 852, 866):
            name = f'P{page}H{height}.BIN'
            batch += (f'C:\\VC\\VCFONT {page} >> LOG.TXT\n'
                      'IF ERRORLEVEL 1 ECHO LOAD FAILED >> FAIL.TXT\n'
                      f'C:\\VC\\PROBE {name}\n')
            expected.append((name, page, height))
        batch += (f'C:\\VC\\VCFONT AUTO >> LOG.TXT\n'
                  'IF ERRORLEVEL 1 ECHO AUTO FAILED >> FAIL.TXT\n'
                  f'C:\\VC\\PROBE A{height}.BIN\n'
                  'C:\\VC\\VCFONT ROM >> LOG.TXT\n'
                  'IF ERRORLEVEL 1 ECHO ROM FAILED >> FAIL.TXT\n'
                  f'C:\\VC\\PROBE S{height}.BIN\n')
    batch += ('C:\\VC\\VCFONT 999 >> LOG.TXT\n'
              'IF NOT ERRORLEVEL 1 ECHO INVALID ACCEPTED >> FAIL.TXT\n'
              'C:\\VC\\PROBE E1.BIN\n'
              'DEL C:\\VC\\FONTS\\CP437.F08\n'
              'C:\\VC\\VCFONT 437 >> LOG.TXT\n'
              'IF NOT ERRORLEVEL 1 ECHO MISSING ACCEPTED >> FAIL.TXT\n'
              'C:\\VC\\PROBE E2.BIN\n'
              'ECHO SHORT > C:\\VC\\FONTS\\CP437.F08\n'
              'C:\\VC\\VCFONT 437 >> LOG.TXT\n'
              'IF NOT ERRORLEVEL 1 ECHO CORRUPT ACCEPTED >> FAIL.TXT\n'
              'C:\\VC\\PROBE E3.BIN\n'
              )
    for mode in ('b14', 'gfx'):
        batch += (f'C:\\VC\\PROBE {mode}\n'
                  f'C:\\VC\\PROBE {mode}B.BIN\n'
                  'C:\\VC\\VCFONT 850 >> LOG.TXT\n'
                  'IF NOT ERRORLEVEL 1 ECHO UNSUPPORTED MODE ACCEPTED >> FAIL.TXT\n'
                  f'C:\\VC\\PROBE {mode}A.BIN\n')
    batch += 'ECHO DONE > DONE.TXT\nC:\\QEXIT.COM\n'
    put('AUTOEXEC.BAT', batch)
    (out / 'QEXIT.COM').write_bytes(bytes.fromhex('baf400b000eecd20'))
    run('mcopy', '-o', '-i', image, str(out / 'QEXIT.COM'), '::/')
    with (out / 'qemu.log').open('wb') as log:
        p = subprocess.Popen(['qemu-system-i386', '-machine', 'pc', '-accel', 'tcg',
            '-cpu', '486', '-m', '64', '-display', 'none', '-monitor', 'none',
            '-serial', 'none', '-drive', 'format=raw,file=' + str(disk), '-boot', 'c',
            '-nic', 'none', '-no-reboot', '-device', 'isa-debug-exit,iobase=0xf4,iosize=1'],
            stdout=log, stderr=log)
        try:
            code = p.wait(timeout=55)
            if code != 1:
                raise RuntimeError(f'QEMU returned {code}; see {out}')
        finally:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=5)
    for pattern in ('*.BIN', 'LOG.TXT', 'DONE.TXT'):
        run('mcopy', '-i', image, '::/' + pattern, str(out) + '/')
    failure = subprocess.run(['mtype', '-i', image, '::/FAIL.TXT'], capture_output=True)
    if failure.stdout.strip():
        raise AssertionError(failure.stdout.decode())
    def read(name):
        return (out / name.upper()).read_bytes()
    report = []
    for name, page, height in expected:
        data = read(name)
        baseline = read(f'R{height}.BIN')
        assert len(data) == 8200 and data[:8] == baseline[:8], name + ': geometry changed'
        assert struct.unpack_from('<H', data, 1)[0] == height
        actual = b''.join(data[8+i*32:8+i*32+height] for i in range(256))
        expected_pixels = (ROOT / f'build/fonts/FONTS/CP{page}.F{height:02}').read_bytes()
        assert actual == expected_pixels, name + ': font pixels differ'
        report.append({'codepage': page, 'height': height, 'glyphs_verified': 256})
    for height in (8, 16):
        assert read(f'R{height}.BIN') == read(f'S{height}.BIN'), 'ROM restore differs'
        data = read(f'A{height}.BIN')
        actual = b''.join(data[8+i*32:8+i*32+height] for i in range(256))
        # The supplied test image uses DOS codepage 437 or 850.
        assert any(actual == (ROOT / f'build/fonts/FONTS/CP{p}.F{height:02}').read_bytes()
                   for p in (437, 850, 852, 866)), 'AUTO did not load supported codepage'
    assert read('S8.BIN') == read('E1.BIN') == read('E2.BIN') == read('E3.BIN'), 'error changed VGA state'
    assert read('B14B.BIN') == read('B14A.BIN'), '8x14 rejection changed font or geometry'
    # In graphics mode, printing the error changes framebuffer pixels. Only
    # compare geometry; ERRORLEVEL above independently verifies rejection.
    assert read('GFXB.BIN')[:8] == read('GFXA.BIN')[:8], 'graphics rejection changed mode'
    (out / 'report.json').write_text(json.dumps({'maxtext': bool(args.maxtext), 'fonts': report,
        'driver_sha256': {n: hashlib.sha256((args.maxtext / n).read_bytes()).hexdigest()
                          for n in ('MAXTEXT.SYS', 'MAXTEXT.COM')} if args.maxtext else {},
        'auto': 'passed', 'rom_restore': 'passed', 'invalid_missing_corrupt': 'passed', 'unsupported_14_graphics': 'passed'}, indent=2) + '\n')
    print(f'PASS: {len(report)*256} glyphs, geometry, AUTO, ROM and errors; {out}')


if __name__ == '__main__':
    main()
