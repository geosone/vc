# vc - the Volkov Commander 4.99.10 alpha, built with JWasm and JWlink

The [Volkov Commander](https://vc.vvv.kyiv.ua/) is a two-panel file manager
for DOS in the style of the Norton Commander, by Vsevolod V. Volkov. Its
author published the sources under the BSD 2-clause license
(<https://vc.vvv.kyiv.ua/download/src/>). The newest of them is 4.99.09
alpha (16.07.2000); the newest program he released is 4.99.08 alpha.
4.99.09 was not finished: it has no help viewer. This repository builds it
with JWasm and JWlink, adds the help (F1) and calls the result 4.99.10
alpha.

| Directory | Content |
|---|---|
| `src/` | the sources of `vc49909.zip`, changed so that [JWasm](https://github.com/Baron-von-Riedesel/JWasm) and JWlink build them (the author used Borland TASM and LINK) |
| `files/` | the other files of the 4.99.08 alpha package: menus, extension files, code page tables, texts, the icon |
| `help/` | the help files (F1) of VC 4.05: English, German, Russian, Polish, Slovak (`help/SOURCES.TXT`) |
| `install/` | `INSTALL.INI` for the [GeosOne Dual Installer](https://github.com/geosone/gdi) |
| `tools/` | `tasm2jwasm.py`, the converter that made `src/` |
| `addons/` | independently written DOS helpers and [German instructions](addons/README.de.md) for the ZIP/ARJ/ACE menus, file lists and batch commands |
| `tests/` | helper command-line tests and a native DOS/QEMU smoke test |

## Building

    make                    # build/VC.COM, build/VC.OVL
    make release            # build/release/ and build/vc49910a.zip
    make disk               # build/vc49910a.img, a 1.44 MB disk
    make check              # gdicheck of the release
    make JWLINK=/path/to/jwlink

Needs GNU make, JWasm 2.x and JWlink; `release` also needs `zip` and
`INSTALL.EXE` of the GeosOne Dual Installer (`GDI=`, default
`../gdi/build`), `disk` needs mtools. Under DOS, `src/MAKE.BAT` is meant to build with
`JWASM.EXE` and `JWLINK.EXE` (`MAKE VC`, `MAKE VCOVL`; not tested yet).

The helper `VCTOOLS.EXE` also needs Open Watcom (`WATCOM=/opt/watcom`,
`WCL=$(WATCOM)/binl64/wcl` by default). It targets 8086 DOS. `make test`
builds the same C89 helper with the host C compiler and runs its tests.
For the main Commander alone, build `build/VC.COM build/VC.OVL`.

The release installs with `INSTALL` from the disk or the directory: it
copies the Commander to `C:\VC`, optionally puts it into the `PATH` and adds
it to the Program Manager of Windows. It asks for the language of the help
and proposes the one of `COUNTRY=` in `CONFIG.SYS`; that help file becomes
`VC.HLP`. `INSTALL /U` in `C:\VC` removes it
again; an update keeps `VC.INI` and the menus and extension files.

## From TASM to JWasm

`tools/tasm2jwasm.py` converted the published sources; `make port` downloads
them (checked by SHA-256), converts them again to `build/port/` and compares
that with `src/`. The changes:

- the TASM features MASM does not have (`LOCALS`/`@@` labels, labels in
  PROCs that are global in TASM, `USES` lines, `LOCAL n:TYPE:count`, nested
  PROCs, `LABEL` in structures, structure initializers, ...), listed at the
  top of the script;
- TASM's `JUMPS` also extends `LOOP` and `JCXZ` when the target is out of
  range (`LOOP +2`, `JMP SHORT +3`, `JMP target`, as in the 4.99.08 program);
  JWasm extends conditional jumps only, so those eight lines are written so;
- the stack of `VC.OVL` is no longer in DGROUP: with it, DGROUP is larger
  than 64 KB (JWlink refuses that); the program runs on its own stack
  segment, as 4.99.08 does;
- by hand: `WORD PTR` in one `CMP` of `VC.ASM`, and `MAKE.BAT`.

The programs are built with `OFFICIAL` defined (`-DOFFICIAL`), as the
author's releases were (4.99.08 shows its "THIS IS ONLY A TEST VERSION"):
without it, `VC.OVL` carries 15 KB of filler and the cursor is never
hidden. This build suppresses the startup test-version message.

`make port` also shows the changes made after the port: the help (below)
the version 4.99.10, and the `!$` / `%$` installation-directory macro.

Before the help was added, the programs JWlink linked were the same as
those JWasm made on its own (`-bin`, and `-mz` before the stack was moved),
up to four far calls into `Subs2` in `VC.OVL` that JWlink writes with
another segment base for the same address.

## State

Tested in QEMU under MS-DOS 7.1: setup from the disk (`INSTALL /S`), start
(only 1.9 KB stay resident), the pull-down menus, Memory Info, the viewer
(F3), copying a file (F5) and quitting (F10, `VC.INI` is written).

## Help (F1)

4.99.09 has the help pages, the buffer and the calls of the help, but no
help viewer (`CALL Help` was commented out). `src/VCHELP.INC` adds one: it
reads `VC.HLP` (Norton Guides, as in 4.05) from the directory of the
Commander and shows the index or a topic in a dialog of 4.99 (scroll bar,
mouse; menu `[ Next ] [ Previous ] [ Index ] [ Cancel ]`). The help page
of the panel, dialog, viewer or editor selects the topic; `HelpMap` gives
the topic of 4.05 for each page of 4.99 (new pages such as Quick View
or the option dialogs get the nearest one).

Tested in QEMU: F1 in the panels (the index), in the copy dialog (Copy), in
the viewer (keyboard reference), Next, Index, Esc; setup with `COUNTRY=049`
installs and shows the German help.

## License

BSD 2-clause license (`LICENSE`, also `src/LICENSE.TXT`): the Volkov
Commander, and the changes and tools of this repository.

## Small extensions

F2, then F3 ("Erweiterungen...") opens the new ZIP, ARJ, ACE and file-list
menus. Archive creation, testing and extraction use external DOS packers
in PATH; none of those packers are distributed here. `VCTOOLS.EXE` provides
file-list formatting, full short paths, commands for each selected file
(including dry run), signature recognition, ZIP central-directory listing
without an external packer, and a read-only hex dump.

The new menu macro `!$` (also `%$`) expands to VC's installation directory
with its trailing backslash. This lets menus find the helper without
requiring VC in PATH. List and batch helpers use VC's short-name macros
for DOS file access. The installer preserves existing user menus on update;
add an `addons.mnu` submenu to your existing VC.MNU to enable them there.

See [the German guide](addons/README.de.md), installed as `ADDONS.TXT`, for
commands, dependencies and limits. These helpers are independent source
implementations of a subset of the old add-ons' functionality. Downloaded
third-party programs, NTFS/LFN drivers and version-specific binary patches
are not included. ZIP64 and multi-volume ZIP archives are not supported.
