/* Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
 * Independent VC helpers; no code from the downloaded add-ons is used.
 * C89, Open Watcom 16-bit DOS or a hosted C compiler.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <limits.h>
#ifdef __WATCOMC__
#include <direct.h>
#else
#include <unistd.h>
#endif

#define LINE_SIZE 1024
#define CMD_SIZE 127
static char line[LINE_SIZE], work[LINE_SIZE];

static int error(const char *message)
{
    fprintf(stderr, "VCTOOLS: %s\n", message);
    return 1;
}

/* Accept VC's CRLF lists, LF lists, and quotes around long names.
 * Never silently split an overlong entry into two commands. */
static int entry(FILE *f)
{
    size_t n;
    if (!fgets(line, sizeof(line), f)) return ferror(f) ? -1 : 0;
    n = strlen(line);
    if (n && line[n-1] != '\n' && !feof(f)) {
        int c = fgetc(f);
        if (c != EOF) return -1;
        if (ferror(f)) return -1;
    }
    while (n && (line[n-1] == '\r' || line[n-1] == '\n')) line[--n] = 0;
    if (n >= 2 && line[0] == '"' && line[n-1] == '"') {
        memmove(line, line+1, n-2);
        line[n-2] = 0;
    }
    return 1;
}

static int listing(int argc, char **argv)
{
    FILE *f;
    int status, full = 0, arg = 3;
    const char *prefix = "", *suffix = "";
    if (argc > arg && !strcmp(argv[arg], "--full")) { full = 1; ++arg; }
    if (argc > arg) prefix = argv[arg++];
    if (argc > arg) suffix = argv[arg++];
    if (argc > arg) return error("too many list arguments");
    f = fopen(argv[2], "r");
    if (!f) return error("cannot open file list");
    while ((status = entry(f)) > 0) {
        const char *name = line;
        if (!*line) continue;
        if (full) {
#ifdef __WATCOMC__
            if (!_fullpath(work, line, sizeof(work))) { status = -1; break; }
#else
            if (line[0] != '/') {
                size_t n;
                if (!getcwd(work, sizeof(work))) { status = -1; break; }
                n = strlen(work);
                if (n + strlen(line) + 2 > sizeof(work)) { status = -1; break; }
                work[n++] = '/';
                strcpy(work+n, line);
            } else strcpy(work, line);
#endif
            name = work;
        }
        if (printf("%s%s%s\n", prefix, name, suffix) < 0) { status = -1; break; }
    }
    fclose(f);
    if (status < 0) return error("list read, path length or output error");
    return 0;
}

/* A file name must remain one quoted argument, even with COMMAND.COM.
 * Reject shell expansion/metacharacters rather than interpreting file names.
 */
static int safe_name(const char *name)
{
    const unsigned char *p = (const unsigned char *)name;
    if (!*p) return 0;
    for (; *p; ++p)
        if (*p < 32 || strchr("\"&|<>^%!`$", *p)) return 0;
    return 1;
}

static int expand(const char *pattern, const char *name, char *out)
{
    size_t used = 0, n = strlen(name);
    int replaced = 0;
    if (!safe_name(name)) return 0;
    while (*pattern) {
        if (pattern[0] == '{' && pattern[1] == '}') {
            if (used + n + 2 >= CMD_SIZE) return 0;
            out[used++] = '"';
            memcpy(out+used, name, n); used += n;
            out[used++] = '"';
            pattern += 2; replaced = 1;
        } else {
            if (used + 1 >= CMD_SIZE) return 0;
            out[used++] = *pattern++;
        }
    }
    out[used] = 0;
    return replaced;
}

static int execute(int argc, char **argv)
{
    FILE *f;
    int status, dry = 0;
    char command[CMD_SIZE];
    if (argc == 5 && !strcmp(argv[4], "--dry-run")) dry = 1;
    else if (argc != 4) return error("run needs LIST and a quoted command with {}");
    f = fopen(argv[2], "r");
    if (!f) return error("cannot open file list");
    while ((status = entry(f)) > 0) {
        if (!*line) continue;
        if (!expand(argv[3], line, command)) {
            fclose(f);
            return error("unsafe name, command over 126 bytes, or missing {}");
        }
        puts(command);
        fflush(stdout);
        if (!dry && system(command) != 0) {
            fclose(f);
            return error("command failed; remaining files were not processed");
        }
    }
    fclose(f);
    return status < 0 ? error("file list read error or entry too long") : 0;
}

static unsigned short u16(const unsigned char *p)
{
    return (unsigned short)(p[0] | ((unsigned short)p[1] << 8));
}

static unsigned long u32(const unsigned char *p)
{
    return (unsigned long)u16(p) | ((unsigned long)u16(p+2) << 16);
}

static int identify(const char *path)
{
    unsigned char b[512];
    FILE *f = fopen(path, "rb");
    size_t n, i;
    const char *kind = "Unknown binary data";
    int text = 1;
    if (!f) return error("cannot open input file");
    n = fread(b, 1, sizeof(b), f);
    if (ferror(f)) { fclose(f); return error("input read error"); }
    fclose(f);
    for (i = 0; i < n; ++i)
        if (b[i] < 32 && b[i] != 9 && b[i] != 10 && b[i] != 13 && b[i] != 26)
            text = 0;
    if (!n) kind = "Empty file";
    else if (n >= 4 && (!memcmp(b, "PK\003\004", 4) ||
             !memcmp(b, "PK\005\006", 4) || !memcmp(b, "PK\007\010", 4)))
        kind = "ZIP archive";
    else if (n >= 7 && !memcmp(b, "Rar!\032\007", 6)) kind = "RAR archive";
    else if (n >= 2 && b[0] == 0x60 && b[1] == 0xea) kind = "ARJ archive";
    else if (n >= 14 && !memcmp(b+7, "**ACE**", 7)) kind = "ACE archive";
    else if (n >= 7 && b[2] == '-' && b[3] == 'l' &&
             (b[4] == 'h' || b[4] == 'z') && b[6] == '-') kind = "LHA/LZH archive";
    else if (n >= 6 && !memcmp(b, "7z\274\257\047\034", 6)) kind = "7-Zip archive";
    else if (n >= 2 && b[0] == 31 && b[1] == 139) kind = "gzip stream";
    else if (n >= 4 && !memcmp(b, "MSCF", 4)) kind = "Microsoft CAB archive";
    else if (n >= 262 && !memcmp(b+257, "ustar", 5)) kind = "TAR archive";
    else if (n >= 2 && (!memcmp(b, "MZ", 2) || !memcmp(b, "ZM", 2)))
        kind = "DOS/Windows executable (MZ)";
    else if (n >= 4 && !memcmp(b, "\177ELF", 4)) kind = "ELF executable";
    else if (n >= 5 && !memcmp(b, "%PDF-", 5)) kind = "PDF document";
    else if (n >= 6 && (!memcmp(b, "GIF87a", 6) || !memcmp(b, "GIF89a", 6)))
        kind = "GIF image";
    else if (n >= 8 && !memcmp(b, "\211PNG\r\n\032\n", 8)) kind = "PNG image";
    else if (n >= 3 && b[0] == 255 && b[1] == 216 && b[2] == 255) kind = "JPEG image";
    else if (n >= 2 && !memcmp(b, "BM", 2)) kind = "BMP image";
    else if (n >= 12 && !memcmp(b, "RIFF", 4) && !memcmp(b+8, "WAVE", 4))
        kind = "WAV audio";
    else if (text) kind = "Text (first 512 bytes; encoding not determined)";
    printf("%s: %s\n", path, kind);
    return 0;
}

static void print_name(const unsigned char *name, size_t n)
{
    size_t i;
    for (i = 0; i < n; ++i) putchar(name[i] < 32 || name[i] == 127 ? '?' : name[i]);
}

/* Read the ZIP central directory; no decompressor or external packer needed.
 * Classic single-disk ZIP only. Bounds are checked before seeking/skipping.
 */
static int ziplist(const char *path)
{
    FILE *f = fopen(path, "rb");
    unsigned char b[1024], h[46];
    long size, end = -1, start, stop, top, cdend, base;
    unsigned long cdsize, cdoffset;
    unsigned short count, i;
    int j;
    size_t got;
    if (!f) return error("cannot open ZIP file");
    if (fseek(f, 0, SEEK_END) || (size = ftell(f)) < 22) goto bad;
    stop = size > 65557L ? size - 65557L : 0;
    top = size;
    while (top > stop && end < 0) {
        start = top - (long)sizeof(b);
        if (start < stop) start = stop;
        if (fseek(f, start, SEEK_SET)) goto bad;
        got = fread(b, 1, (size_t)(top-start), f);
        if (got != (size_t)(top-start)) goto bad;
        for (j = (int)got-4; j >= 0; --j) {
            if (memcmp(b+j, "PK\005\006", 4)) continue;
            if (size - (start+j) < 22) continue;
            if (fseek(f, start+j, SEEK_SET) || fread(h, 1, 22, f) != 22) goto bad;
            if ((long)u16(h+20) == size - (start+j) - 22) {
                end = start+j; break;
            }
        }
        if (start == stop) break;
        top = start+3; /* signatures crossing a block boundary */
    }
    if (end < 0) goto bad;
    if (u16(h+4) || u16(h+6) || u16(h+8) != u16(h+10)) goto unsupported;
    count = u16(h+10); cdsize = u32(h+12); cdoffset = u32(h+16);
    if (count == 65535U || cdsize == 0xffffffffUL || cdoffset == 0xffffffffUL)
        goto unsupported;
    if (cdsize > (unsigned long)end || cdoffset > (unsigned long)end - cdsize)
        goto bad;
    base = end - (long)cdsize - (long)cdoffset; /* self-extracting prefix */
    cdend = end;
    if (fseek(f, base+(long)cdoffset, SEEK_SET)) goto bad;
    puts("      Size     Packed Method Name");
    for (i = 0; i < count; ++i) {
        unsigned short namesize, extrasize, commentsize;
        unsigned long unpacked, packed;
        long pos = ftell(f);
        if (pos < 0 || pos > cdend || cdend-pos < 46) goto bad;
        if (fread(h, 1, 46, f) != 46 || memcmp(h, "PK\001\002", 4)) goto bad;
        namesize = u16(h+28); extrasize = u16(h+30); commentsize = u16(h+32);
        packed = u32(h+20); unpacked = u32(h+24);
        if (packed == 0xffffffffUL || unpacked == 0xffffffffUL ||
            u32(h+42) == 0xffffffffUL) goto unsupported;
        if (u16(h+34)) goto unsupported;
        if ((long)namesize + extrasize + commentsize > cdend-pos-46) goto bad;
        if (!namesize || namesize > sizeof(b)) goto bad;
        if (fread(b, 1, namesize, f) != namesize) goto bad;
        printf("%10lu %10lu %6u ", unpacked, packed, (unsigned)u16(h+10));
        print_name(b, namesize); putchar('\n');
        if (fseek(f, (long)extrasize+commentsize, SEEK_CUR)) goto bad;
    }
    if (ftell(f) != cdend) goto bad;
    printf("%u entries\n", (unsigned)count);
    fclose(f);
    return 0;
unsupported:
    fclose(f);
    return error("ZIP64 or multi-disk ZIP is not supported");
bad:
    fclose(f);
    return error("invalid, truncated or unsupported ZIP directory");
}

static int hexdump(int argc, char **argv)
{
    FILE *f;
    unsigned char b[16];
    char *end;
    unsigned long offset = 0, length = 256, done = 0;
    size_t n, i;
    if (argc > 3) {
        if (*argv[3] == '-') return error("invalid offset");
        offset = strtoul(argv[3], &end, 0);
        if (!*argv[3] || *end || offset > LONG_MAX) return error("invalid offset");
    }
    if (argc > 4) {
        if (*argv[4] == '-') return error("invalid length");
        length = strtoul(argv[4], &end, 0);
        if (!*argv[4] || *end || length > LONG_MAX) return error("invalid length");
    }
    if (argc > 5) return error("too many hex arguments");
    if (length > (unsigned long)LONG_MAX-offset) return error("range too large");
    f = fopen(argv[2], "rb");
    if (!f) return error("cannot open input file");
    if (fseek(f, (long)offset, SEEK_SET)) { fclose(f); return error("seek failed"); }
    while (done < length) {
        n = fread(b, 1, length-done < 16 ? (size_t)(length-done) : 16, f);
        if (!n) break;
        printf("%08lX  ", offset+done);
        for (i = 0; i < 16; ++i) {
            if (i < n) printf("%02X ", (unsigned)b[i]); else fputs("   ", stdout);
        }
        putchar(' ');
        for (i = 0; i < n; ++i) putchar(b[i] >= 32 && b[i] < 127 ? b[i] : '.');
        putchar('\n'); done += n;
    }
    n = ferror(f);
    fclose(f);
    return n ? error("input read error") : 0;
}

static void usage(void)
{
    puts("VCTOOLS - independent helpers for Volkov Commander\n"
         "  VCTOOLS list LIST [--full] [PREFIX [SUFFIX]]\n"
         "  VCTOOLS run LIST \"COMMAND {}\" [--dry-run]\n"
         "  VCTOOLS type FILE\n"
         "  VCTOOLS zip FILE\n"
         "  VCTOOLS hex FILE [OFFSET [LENGTH]]\n"
         "Lists, ZIP contents and hex dumps go to standard output.\n"
         "Run quotes each {} file name and stops on the first error.\n"
         "Use 8.3 names under DOS; VC can generate these with !~@.");
}

int main(int argc, char **argv)
{
    int rc;
    if (argc == 1 || (argc == 2 && !strcmp(argv[1], "--help"))) {
        usage(); return 0;
    }
    if (argc < 3) { usage(); return 1; }
    if (!strcmp(argv[1], "list")) rc = listing(argc, argv);
    else if (!strcmp(argv[1], "run")) rc = execute(argc, argv);
    else if (!strcmp(argv[1], "type") && argc == 3) rc = identify(argv[2]);
    else if (!strcmp(argv[1], "zip") && argc == 3) rc = ziplist(argv[2]);
    else if (!strcmp(argv[1], "hex")) rc = hexdump(argc, argv);
    else { usage(); return 1; }
    if (fflush(stdout) || ferror(stdout)) return error("output write error");
    return rc;
}
