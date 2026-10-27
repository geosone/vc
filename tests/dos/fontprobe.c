/* Independent VGA plane reader used only by the DOS integration test.
 * Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause */
#include <stdio.h>
#include <string.h>
#include <i86.h>
#include <conio.h>
#include <dos.h>
static unsigned char data[8192];
static unsigned char header[8];
int main(int argc, char **argv)
{
    union REGPACK r;
    unsigned char si, gi, s2, s4, g4, g5, g6;
    FILE *f;
    if (argc != 2) return 1;
    if (strcmp(argv[1], "b8") == 0 || strcmp(argv[1], "b16") == 0 ||
        strcmp(argv[1], "b14") == 0 || strcmp(argv[1], "gfx") == 0) {
        memset(&r, 0, sizeof(r)); r.w.ax = strcmp(argv[1], "gfx") == 0 ? 0x13 : 3; intr(0x10, &r);
        if (strcmp(argv[1], "b8") == 0) {
            memset(&r, 0, sizeof(r)); r.w.ax = 0x1112; intr(0x10, &r);
        }
        if (strcmp(argv[1], "b14") == 0) {
            memset(&r, 0, sizeof(r)); r.w.ax = 0x1111; intr(0x10, &r);
        }
        return 0;
    }
    _fmemcpy(header, MK_FP(0x40, 0x84), 3); /* rows-minus-one, height word */
    _fmemcpy(header+3, MK_FP(0x40, 0x4a), 2); /* columns */
    header[5] = *(unsigned char __far *)MK_FP(0x40, 0x49);
    header[6] = *(unsigned char __far *)MK_FP(0x40, 0x62);
    _disable();
    si = inp(0x3c4); gi = inp(0x3ce);
    outp(0x3c4, 2); s2 = inp(0x3c5);
    outp(0x3c4, 4); s4 = inp(0x3c5);
    outp(0x3ce, 4); g4 = inp(0x3cf);
    outp(0x3ce, 5); g5 = inp(0x3cf);
    outp(0x3ce, 6); g6 = inp(0x3cf);
    outpw(0x3c4, 0x0402); outpw(0x3c4, 0x0704);
    outpw(0x3ce, 0x0204); outpw(0x3ce, 0x0005); outpw(0x3ce, 0x0406);
    _fmemcpy(data, MK_FP(0xa000, 0), sizeof(data));
    outpw(0x3c4, (s2 << 8) | 2); outpw(0x3c4, (s4 << 8) | 4);
    outpw(0x3ce, (g4 << 8) | 4); outpw(0x3ce, (g5 << 8) | 5);
    outpw(0x3ce, (g6 << 8) | 6);
    outp(0x3c4, si); outp(0x3ce, gi);
    _enable();
    f = fopen(argv[1], "wb");
    if (!f) return 1;
    if (fwrite(header, 1, 8, f) != 8 || fwrite(data, 1, sizeof(data), f) != sizeof(data)) {
        fclose(f); return 1;
    }
    return fclose(f) != 0;
}
