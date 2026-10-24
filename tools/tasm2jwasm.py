#!/usr/bin/env python3
"""tasm2jwasm.py [-x FILE:LINE ...] SRC DST: the TASM sources of the Volkov
Commander, as published (vc49909.zip), in a form JWasm and JWlink build,
written to DST.  It made src/ of this repository (`make port` does it again
and compares).

TASM features the sources use and what they become:
  LOCALS @@ / @@name   a local label is valid in its PROC (so in MASM with
                       OPTION M510 and SCOPED, added after .MODEL); outside
                       PROCs between two non-local labels: it becomes
                       @@name_Label after the label Label
  label: in a PROC     global in TASM, local in MASM: label::
  JUMPS                conditional jumps out of range: JWasm extends them
                       itself (OPTION LJMP), the line is commented out
  name PROC / USES r,r USES on the next line goes onto the PROC line
  name LABEL           without a type: LABEL BYTE; inside STRUC (MASM has
                       no LABEL there): an array of 0 elements
                       that takes an item in <...> initializers, so they get
                       an empty one at its place
  name STRUCNAME ?     a structure initialized with ?: <> (also DUP(?))
  SIZE STRUCNAME       SIZEOF, or the size itself (-s FILE: a JWasm listing
                       of a first run; JWasm cannot size a structure defined
                       further down)
  (SIZE S-1)/16+1      (SIZEOF S+15)/16, the same number of paragraphs: JWasm
                       cannot take the first form while S is defined later
  LOCAL n:TYPE:count   LOCAL n[count]:TYPE; USES after LOCAL lines goes onto
                       the PROC line too
  PROC in a PROC       a label (label::); its RET becomes RETN/RETF (MASM would add
                       the epilogue of the outer PROC), its ENDP is dropped
  LEA r,OFFSET local   LEA r,local
  LOOP/JCXZ too far    as TASM does with JUMPS: LOOP +2 / JMP SHORT +3 /
                       JMP target (-x FILE:LINE, the lines JWasm reports
                       out of range; GNUmakefile names them)
  DS:DS:var            one DS: too many
  .MODEL Tiny          DOSSEG before it: TASM orders the segments as DOS
                       does (code, data, BSS last), JWasm otherwise in the
                       order they appear (.DATA? comes first in VC.ASM)
  .MODEL Medium        FARSTACK, and .STACK at the end: a stack in DGROUP
                       makes it larger than 64 KB (JWlink refuses it); VC.OVL
                       runs on its own stack segment

Copyright (C) 2026 GeosOne.  BSD 2-clause license, as the Volkov Commander
(LICENSE)."""

import re
import sys
from pathlib import Path

LABEL = re.compile(r'^\s*([A-Za-z_?$][\w?$]*)\s*:(?!:)')
PROC = re.compile(r'^\s*([A-Za-z_?$][\w?$]*)\s+PROC\b', re.I)
LABELDIR = re.compile(r'^(\s*[A-Za-z_?$][\w?$]*\s+LABEL)\s*(;.*)?$', re.I)
TYPEDLABEL = re.compile(r'^\s*[A-Za-z_?$][\w?$]*\s+LABEL\b', re.I)
USES = re.compile(r'^\s*USES\s+([^;]*?)\s*(;.*)?$', re.I)
LOCAL = re.compile(r'@@(\w+)')

scope = 0
scopes = 0


def counter():
    global scopes
    scopes += 1
    return scopes


structs = set()
labelpos = {}       # structure: the field numbers of its LABELs
far = set()         # (FILE, line): a LOOP/JCXZ out of range
STRUC = re.compile(r'^\s*([A-Za-z_?$][\w?$]*)\s+(STRUC|STRUCT|UNION)\b', re.I)
ENDS = re.compile(r'^\s*[A-Za-z_?$][\w?$]*\s+ENDS\b', re.I)
INLABEL = re.compile(r'^(\s*[A-Za-z_?$][\w?$]*\s+)LABEL\s+(BYTE|WORD|DWORD)\b', re.I)
SIZES = {'BYTE': 'DB', 'WORD': 'DW', 'DWORD': 'DD'}


def code_part(line):
    """the line up to its comment (quotes respected)"""
    q = None
    for i, c in enumerate(line):
        if q:
            if c == q:
                q = None
        elif c in '\'"':
            q = c
        elif c == ';':
            return line[:i], line[i:]
    return line, ''


def split_items(text):
    """the items of an initializer list (commas at the top level)"""
    items, depth, q, cur = [], 0, None, ''
    for c in text:
        if q:
            q = None if c == q else q
        elif c in '\'"':
            q = c
        elif c in '<({':
            depth += 1
        elif c in '>)}':
            depth -= 1
        elif c == ',' and depth == 0:
            items.append(cur)
            cur = ''
            continue
        cur += c
    items.append(cur)
    return items


def fix_init(struct, init):
    m = re.match(r'^(\s*)<(.*)>(\s*)$', init)
    if not m or struct not in labelpos:
        return init
    items = split_items(m.group(2))
    for pos in labelpos[struct]:
        if pos <= len(items):
            items.insert(pos, '')
    return m.group(1) + '<' + ','.join(items) + '>' + m.group(3)


def size_of(m):
    name = m.group(2).upper()
    return ('SIZEOF' if name in structs else m.group(0).split()[0]) + m.group(1) + m.group(2)


names = {}         # scope: None (a PROC: MASM keeps @@ labels local there)
                   # or the label or nested PROC that begins it


def local_name(m):
    if names.get(scope) is None:
        return m.group(0)
    return '@@%s_%s' % (m.group(1), names[scope])


def convert(text, name=''):
    global scope
    out = []
    instruc = False
    stack = None        # the .STACK line: it goes to the end
    procs = []          # the open PROCs: [name, distance, nested]
    for number, line in enumerate(text.split('\n'), 1):
        code, comment = code_part(line.rstrip('\r'))
        m = re.match(r'^(\s*(?:[\w@?$]+:)?\s*)(LOOP\w*|JCXZ)\s+(\S+)\s*$', code, re.I)
        if m and (name.upper(), number) in far:
            n = counter()
            code = ('%s%s @@Far%d\n\t\tJMP SHORT @@Near%d\n  @@Far%d:\tJMP %s\t; TASM JUMPS: %s %s'
                    '\n  @@Near%d:') % (m.group(1), m.group(2), n, n, n, m.group(3),
                                      m.group(2).upper(), m.group(3), n)
        m = re.match(r'^(\s*\.MODEL\s+)(\w+)(.*?)\s*$', code, re.I)
        if m:
            tiny = m.group(2).upper() == 'TINY'
            if tiny:
                code = '\t\tDOSSEG\n' + code
            else:
                code = code.rstrip() + ',FARSTACK'
            # TASM's MASM mode, but labels in PROCs stay local
            code += '\n\t\tOPTION\tM510\n\t\tOPTION\tSCOPED'
        if re.match(r'^\s*\.STACK\b', code, re.I):
            stack = code.strip()
            out.append(';' + code + comment + '\t(at the end, after the data)')
            continue
        if stack and re.match(r'^\s*END\b', code, re.I):
            code = '\t\t' + stack + '\n\n' + code

        if STRUC.match(code):
            instruc = True
        elif ENDS.match(code):
            instruc = False
        code = re.sub(r'\bDS:\s*DS:', 'DS:', code, flags=re.I)
        code = re.sub(r'\(\s*SIZE\s+(\w+)\s*-\s*1\s*\)\s*/\s*16\s*\+\s*1\b',
                      r'(SIZE \1+15)/16', code, flags=re.I)
        code = re.sub(r'\bSIZE(?:OF)?(\s+)(\w+)', size_of, code, flags=re.I)
        m = re.match(r'^(\s*(?:\S+\s+)?)(\w+)(\s+)(.*)$', code)
        if m and m.group(2).upper() in structs and not STRUC.match(code) and not ENDS.match(code):
            init = re.sub(r'^\?', '<>', m.group(4))
            init = re.sub(r'DUP\s*\(\s*\?\s*\)', 'DUP(<>)', init, flags=re.I)
            init = fix_init(m.group(2).upper(), init)
            code = m.group(1) + m.group(2) + m.group(3) + init
        if re.match(r'^\s*(LOCALS|JUMPS)\b', code, re.I):
            out.append(';' + code + comment)
            continue
        m = USES.match(code)
        if m:
            i = len(out) - 1
            while i >= 0 and re.match(r'^\s*(LOCAL\b|$)', code_part(out[i])[0], re.I):
                i -= 1
            if i >= 0 and PROC.match(code_part(out[i])[0]):
                regs = ' '.join(r.strip() for r in m.group(1).split(','))
                pc, pcom = code_part(out[i])
                out[i] = pc.rstrip() + ' USES ' + regs + pcom
                out.append(comment)
                continue
        code = re.sub(r'^(\s*LOCAL\s+)(.*)$', lambda m: m.group(1) + ', '.join(
            re.sub(r'^\s*(\w+)\s*:\s*(\w+)\s*:\s*(.+?)\s*$', r'\1[\3]:\2', v)
            for v in split_items(m.group(2))), code, flags=re.I)
        code = re.sub(r'^(\s*LEA\s+\w+\s*,\s*)OFFSET\s+', r'\1', code, flags=re.I)
        m = PROC.match(code)
        if m:
            dist = 'F' if re.search(r'\bFAR\b', code, re.I) else 'N'
            nested = bool(procs)
            procs.append([m.group(1).upper(), dist, nested, scope])
            scope = counter()
            names[scope] = None if not nested else m.group(1)
            if nested:
                out.append(m.group(1) + '::' + ' ' * 8 + '; PROC ' +
                           code[m.end():].strip() + comment)
                continue
            out.append(code + comment)
            continue
        m = re.match(r'^\s*(\w+)\s+ENDP\b', code, re.I)
        if m and procs and procs[-1][0] == m.group(1).upper():
            p = procs.pop()
            scope = p[3] if p[2] else counter()
            if not p[2]:
                names[scope] = p[0].title() + 'End'

            if p[2]:
                out.append(';' + code + comment)
                continue
        if procs and procs[-1][2]:
            code = re.sub(r'^(\s*(?:\w+:)?\s*)RET\b', lambda m: m.group(1) + 'RET' + procs[-1][1],
                          code, flags=re.I)
        m = INLABEL.match(code)
        if instruc and m:
            code = m.group(1) + SIZES[m.group(2).upper()] + ' 0 DUP(?)'
        elif LABELDIR.match(code):
            code = re.sub(r'\bLABEL\s*$', 'LABEL BYTE', code.rstrip(), flags=re.I) + ' '
        # outside PROCs a non-local label starts a new scope of @@ labels
        m = LABEL.match(code) or (TYPEDLABEL.match(code) and re.match(r'^\s*(\w+)', code))
        if m and not procs and not code.lstrip().startswith('@@'):
            scope = counter()
            names[scope] = (LABEL.match(code) or TYPEDLABEL.match(code)) and re.match(r'^\s*(\w+)', code).group(1)
        if procs:   # a label in a PROC stays global, as in TASM
            code = re.sub(r'^(\s*[A-Za-z_?$][\w?$]*):(?!:)', r'\1::', code)
        code = LOCAL.sub(local_name, code)
        out.append(code + comment)
    return '\n'.join(out)


def main():
    args = sys.argv[1:]
    while args and args[0] == '-x':
        f, l = args[1].rsplit(':', 1)
        far.add((f.upper(), int(l)))
        args = args[2:]
    src, dst = Path(args[0]), Path(args[1])
    dst.mkdir(parents=True, exist_ok=True)
    files = [f for f in sorted(src.iterdir()) if f.suffix.upper() in ('.ASM', '.INC')]
    for f in files:
        cur = None
        for line in f.read_bytes().decode('cp437').split('\n'):
            code = code_part(line)[0]
            m = STRUC.match(code)
            if m:
                cur, n = m.group(1).upper(), 0
                structs.add(cur)
            elif cur and ENDS.match(code):
                cur = None
            elif cur and code.strip():
                if re.search(r'\bLABEL\b', code, re.I):
                    labelpos.setdefault(cur, []).append(n)
                n += 1
    for f in files:
        source = f.read_bytes().decode('cp437')
        text = convert(source, f.name)
        if '\r\n' in source:      # the line ends stay as they were
            text = text.replace('\r\n', '\n').replace('\n', '\r\n')
        (dst / f.name).write_bytes(text.encode('cp437'))


if __name__ == '__main__':
    main()
