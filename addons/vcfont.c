/* VGA font loader for DOS, 8086 small model.
 * Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <i86.h>
#include <dos.h>

static unsigned char pixels[4096];

static void bios(union REGPACK *r)
{
    intr(0x10, r);
}

static int fail(const char *message)
{
    fprintf(stderr, "VCFONT: %s\n", message);
    return 1;
}

int main(int argc, char **argv)
{
    union REGPACK r;
    unsigned height, page = 0, mode, columns, rows, active;
    unsigned short __far *bda = (unsigned short __far *)MK_FP(0x40, 0);
    char path[260], *slash, *other;
    FILE *file;
    size_t count;
    int rom = 0;

    if (argc != 2) {
        puts("VCFONT 437|850|852|866|AUTO|ROM\n"
             "Load Unscii for the current 8- or 16-pixel VGA text mode.\n"
             "Changes display glyphs only; does not select a DOS codepage.");
        return argc == 1 ? 0 : 1;
    }
    if (stricmp(argv[1], "ROM") == 0) rom = 1;
    else if (stricmp(argv[1], "AUTO") == 0) {
        memset(&r, 0, sizeof(r));
        r.w.ax = 0x6601;
        intr(0x21, &r);
        if (r.w.flags & 1) return fail("DOS cannot report the active codepage.");
        page = r.w.bx;
    } else {
        if (strcmp(argv[1], "437") == 0) page = 437;
        else if (strcmp(argv[1], "850") == 0) page = 850;
        else if (strcmp(argv[1], "852") == 0) page = 852;
        else if (strcmp(argv[1], "866") == 0) page = 866;
    }
    if (!rom && page != 437 && page != 850 && page != 852 && page != 866)
        return fail("supported codepages: 437, 850, 852, 866.");

    /* Enhanced-mode Windows, then standard/real-mode Windows. */
    memset(&r, 0, sizeof(r));
    r.w.ax = 0x1600;
    intr(0x2f, &r);
    if ((r.w.ax & 0x7f) != 0) return fail("exit Windows before loading a font.");
    memset(&r, 0, sizeof(r));
    r.w.ax = 0x4680;
    intr(0x2f, &r);
    if (r.w.ax == 0) return fail("exit Windows before loading a font.");
    memset(&r, 0, sizeof(r));
    r.w.ax = 0x1a00;
    bios(&r);
    if ((r.w.ax & 255) != 0x1a || ((r.w.bx & 255) != 7 && (r.w.bx & 255) != 8))
        return fail("VGA text hardware is required.");
    memset(&r, 0, sizeof(r));
    r.w.ax = 0x0f00;
    bios(&r);
    mode = r.w.ax & 0x7f;
    if (mode != 3 && mode != 7) return fail("VGA text mode 3 or 7 is required.");
    columns = bda[0x4a / 2];
    rows = *(unsigned char __far *)MK_FP(0x40, 0x84);
    height = *(unsigned short __far *)MK_FP(0x40, 0x85);
    active = *(unsigned char __far *)MK_FP(0x40, 0x62);
    if (height != 8 && height != 16)
        return fail("only 8- or 16-scanline fonts are supplied (not 8x14).");

    if (!rom) {
        if (strlen(argv[0]) > sizeof(path) - 24) return fail("executable path too long.");
        strcpy(path, argv[0]);
        slash = strrchr(path, '\\');
        other = strrchr(path, '/');
        if (other && (!slash || other > slash)) slash = other;
        if (!slash) slash = strrchr(path, ':');
        if (slash) slash[1] = '\0';
        else path[0] = '\0';
        sprintf(path + strlen(path), "FONTS\\CP%u.F%02u", page, height);
        file = fopen(path, "rb");
        if (!file) return fail("cannot open font beside VCFONT.EXE in FONTS.");
        count = fread(pixels, 1, height * 256, file);
        if (count != height * 256 || fgetc(file) != EOF || ferror(file)) {
            fclose(file);
            return fail("invalid raw font length or read error; display unchanged.");
        }
        fclose(file);
    }
    memset(&r, 0, sizeof(r));
    if (rom) r.w.ax = height == 8 ? 0x1102 : 0x1104;
    else {
        r.w.ax = 0x1100;
        r.w.bx = height << 8; /* BH height, BL font block zero. */
        r.w.cx = 256;
        r.w.es = FP_SEG(pixels);
        r.w.bp = FP_OFF(pixels);
    }
    /* 110x loads patterns only; 111x would also change the video geometry. */
    bios(&r);
    if (bda[0x4a / 2] != columns ||
        *(unsigned char __far *)MK_FP(0x40, 0x84) != rows ||
        *(unsigned short __far *)MK_FP(0x40, 0x85) != height ||
        *(unsigned char __far *)MK_FP(0x40, 0x62) != active)
        return fail("BIOS unexpectedly changed display geometry.");
    if (rom) puts("VCFONT: BIOS ROM font restored.");
    else printf("VCFONT: Unscii CP%u, 8x%u loaded. DOS codepage unchanged.\n", page, height);
    return 0;
}
