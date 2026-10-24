/* Copyright 2026 Mario Fetka. SPDX-License-Identifier: BSD-2-Clause
 * Convert Retro7Zip's technical listing to stable VCARCH.EXT records.
 * Solid archives can omit Packed Size; human listings cannot be parsed
 * reliably when that column is blank. Never parse the archive header.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
#include <ctype.h>
#ifdef __WATCOMC__
#include <io.h>
#include <process.h>
#include <direct.h>
#else
#include <unistd.h>
#include <sys/wait.h>
#endif

static char line[1024], name[1024];
static unsigned long size, packed;
static int folder, header, have_name;
static char date[20], attrs[7];

static void reset(void)
{
    name[0] = 0; size = packed = 0;
    folder = header = have_name = 0;
    strcpy(date, "1980-01-01 00:00:00");
    strcpy(attrs, "....A");
}

static int emit(void)
{
    size_t i;
    if (!have_name || header) return 0;
    if (!*name) return 1;
    for (i = 0; name[i]; ++i)
        if ((unsigned char)name[i] < 32 || (unsigned char)name[i] == 127) return 1;
    if (folder) attrs[0] = 'D';
    printf("VC7Z %s %lu %lu %s ", attrs, size, packed, date);
    for (i = 0; name[i]; ++i) {
        unsigned char c = (unsigned char)name[i];
        putchar(c == '/' ? '\\' : c);
    }
    putchar('\n');
    return ferror(stdout) != 0;
}

static int number(const char *s, unsigned long *value)
{
    char *end;
    if (!*s) { *value = 0; return 0; } /* solid member: no separate packed size */
    if (*s < '0' || *s > '9') return 1;
    errno = 0;
    *value = strtoul(s, &end, 10);
    if (errno || *end) return 1;
#if ULONG_MAX > 0xffffffffUL
    if (*value > 0xffffffffUL) return 1;
#endif
    return 0;
}

static int parse(FILE *f, const char *archive)
{
    reset();
    while (fgets(line, sizeof(line), f)) {
        size_t n = strlen(line);
        if (n == sizeof(line)-1 && line[n-1] != '\n') return 1;
        while (n && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
        /* The pinned DOS release has SHOW_DEBUG_INFO enabled in OpenArchive.cpp.
         * It writes "Open: <archive>" without a final newline, merging the
         * first RAR member's Path record into the debug line. Match the exact
         * argument; a member name itself may contain the words "Path = ". */
        if (archive && !strncmp(line, "Open: ", 6)) {
            size_t prefix = 6 + strlen(archive);
            if (n >= prefix && !strncmp(line+6, archive, strlen(archive))) {
                memmove(line, line+prefix, n-prefix+1); n -= prefix;
            }
        }
        if (!n) { if (emit()) return 1; reset(); }
        else if (!strncmp(line, "Path = ", 7)) {
            if (have_name) { if (emit()) return 1; reset(); }
            strcpy(name, line+7); have_name = 1;
        }
        else if (!strncmp(line, "Type = ", 7)) header = 1;
        else if (!strncmp(line, "Folder = ", 9)) folder = line[9] == '+';
        else if (!strncmp(line, "Size = ", 7)) { if (number(line+7, &size)) return 1; }
        else if (!strncmp(line, "Packed Size = ", 14)) { if (number(line+14, &packed)) return 1; }
        else if (!strncmp(line, "Modified = ", 11) && strlen(line+11) >= 19) {
            size_t i;
            int valid = 1;
            for (i = 0; i < 19; ++i) {
                char c = line[11+i];
                if (i == 4 || i == 7) { if (c != '-') valid = 0; }
                else if (i == 10) { if (c != ' ') valid = 0; }
                else if (i == 13 || i == 16) { if (c != ':') valid = 0; }
                else if (c < '0' || c > '9') valid = 0;
            }
            if (valid && strncmp(line+11, "1980", 4) >= 0 &&
                strncmp(line+11, "2107", 4) <= 0) {
                memcpy(date, line+11, 19); date[19] = 0;
            }
        }
        else if (!strncmp(line, "Attributes = ", 13)) {
            const char *p = line+13;
            while (*p == ' ') ++p;
            for (; *p && *p != ' '; ++p) {
                if (*p == 'D') folder = 1;
                if (*p == 'R') attrs[1] = 'R';
                if (*p == 'H') attrs[2] = 'H';
                if (*p == 'S') attrs[3] = 'S';
            }
        }
    }
    return ferror(f) || emit();
}

static int launch(FILE *f, const char *program, const char *const *args)
{
    fflush(stdout);
#ifdef __WATCOMC__
    {
        int saved, rc;
        if (!f) return spawnv(P_WAIT, program, args) != 0;
        saved = dup(1);
        if (saved < 0) return 1;
        if (dup2(fileno(f), 1) < 0) { close(saved); return 1; }
        rc = spawnv(P_WAIT, program, args);
        if (dup2(saved, 1) < 0) rc = -1;
        close(saved);
        return rc != 0;
    }
#else
    {
        pid_t pid = fork();
        int status;
        if (pid < 0) return 1;
        if (!pid) {
            if (f && dup2(fileno(f), 1) < 0) _exit(127);
            execvp(program, (char *const *)args);
            _exit(127);
        }
        while (waitpid(pid, &status, 0) < 0) if (errno != EINTR) return 1;
        return !WIFEXITED(status) || WEXITSTATUS(status) != 0;
    }
#endif
}

static int run7z(FILE *f, const char *program, const char *archive)
{
    const char *args[8];
    args[0] = program; args[1] = "l"; args[2] = "-slt"; args[3] = "-ba";
    args[4] = "-sccDOS"; args[5] = "--"; args[6] = archive; args[7] = NULL;
    return launch(f, program, args);
}

static int extract(const char *program, const char *archive, const char *dest)
{
    char absolute[1024], original[1024];
    const char *args[7];
    int rc;
#ifdef __WATCOMC__
    int original_drive = _getdrive();
#endif
    if (!getcwd(original, sizeof(original))) return 1;
#ifdef __WATCOMC__
    if (!_fullpath(absolute, archive, sizeof(absolute))) return 1;
#else
    if (*archive == '/') {
        if (strlen(archive) >= sizeof(absolute)) return 1;
        strcpy(absolute, archive);
    } else {
        if (strlen(original)+strlen(archive)+2 > sizeof(absolute)) return 1;
        strcpy(absolute, original); strcat(absolute, "/"); strcat(absolute, archive);
    }
#endif
    /* Retro7Zip 24.09+5 fails with -o for an existing directory on MS-DOS.
     * Running from that directory avoids the upstream mkdir/stat mismatch. */
#ifdef __WATCOMC__
    if (dest[0] && dest[1] == ':' && _chdrive(toupper((unsigned char)dest[0])-'A'+1))
        return 1;
#endif
    if (chdir(dest)) {
#ifdef __WATCOMC__
        _chdrive(original_drive);
#endif
        return 1;
    }
    args[0] = program; args[1] = "x"; args[2] = "-sccDOS";
    args[3] = "--"; args[4] = absolute; args[5] = NULL;
    rc = launch(NULL, program, args);
#ifdef __WATCOMC__
    if (_chdrive(original_drive)) rc = 1;
#endif
    if (chdir(original)) rc = 1;
    return rc;
}

int main(int argc, char **argv)
{
    char program[1024];
    const char *slash, *backslash;
    FILE *f;
    int rc;
    size_t prefix;
    slash = strrchr(argv[0], '/'); backslash = strrchr(argv[0], '\\');
    if (!slash || (backslash && backslash > slash)) slash = backslash;
    prefix = slash ? (size_t)(slash+1-argv[0]) : 0;
    if (prefix + 8 >= sizeof(program)) return 1;
    memcpy(program, argv[0], prefix); strcpy(program+prefix, "7ZA.EXE");
    if (argc == 4 && !strcmp(argv[1], "x"))
        return extract(program, argv[2], argv[3]);
    if ((argc == 3 || argc == 4) && !strcmp(argv[1], "--parse")) {
        f = fopen(argv[2], "r");
        if (!f) return 1;
    } else if (argc == 2 || argc == 3) {
        f = tmpfile();
        if (!f) { fputs("VC7Z: cannot create temporary listing\n", stderr); return 1; }
        if (run7z(f, argc == 3 ? argv[2] : program, argv[1])) {
            fclose(f);
            fputs("VC7Z: 7ZA failed; check archive, CPU and memory\n", stderr);
            return 1;
        }
        if (fseek(f, 0, SEEK_SET)) { fclose(f); return 1; }
    } else {
        fputs("VC7Z ARCHIVE [7ZA-PROGRAM]\nVC7Z x ARCHIVE DIRECTORY\nVC7Z --parse TECHNICAL-LIST\n", stderr);
        return 1;
    }
    rc = parse(f, !strcmp(argv[1], "--parse") ? (argc == 4 ? argv[3] : NULL) : argv[1]);
    fclose(f);
    if (fflush(stdout) || ferror(stdout)) rc = 1;
    if (rc) fputs("VC7Z: invalid listing or value beyond VC's 32-bit file-size limit\n", stderr);
    return rc;
}
