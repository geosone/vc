# Volkov Commander with JWasm and JWlink

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
| `files/` | text files: menus, extension associations and documentation |
| `assets/` | XML character mappings and the SVG icon, compiled by `make assets` |
| `help/` | editable XML help in five languages, DTD/CSS for XMLmind, and provenance for the imported VC 4.05 text; [editing instructions](help/README.md) |
| `install/` | `INSTALL.INI` for the [GeosOne Dual Installer](https://github.com/geosone/gdi) |
| `tools/` | source converter, DOS help compiler and pinned packer downloads |
| `addons/` | independently written DOS helpers and [German instructions](addons/README.de.md) for the ZIP/ARJ/ACE menus, file lists and batch commands |
| `tests/` | helper command-line tests and a native DOS/QEMU smoke test |

## Building

    make                    # build/VC.COM, build/VC.OVL
    make assets             # generate TBL files and VC.ICO from XML/SVG
    make help               # compile XML sources to five DOS HLP guides
    make release            # build/release/ and build/vc49910a.zip
    make disk               # build/vc49910a.img, a 1.44 MB disk
    make check              # gdicheck of the release
    make packers            # pinned downloads, verify cache, stage DOS packers
    make JWLINK=/path/to/jwlink

Needs Python 3, GNU make, JWasm 2.x and JWlink; `release` also needs `zip` and
`INSTALL.EXE` of the GeosOne Dual Installer (`GDI=`, default
`../gdi/build`), `disk` needs mtools. Under DOS, `src/MAKE.BAT` is meant to build with
`JWASM.EXE` and `JWLINK.EXE` (`MAKE VC`, `MAKE VCOVL`; not tested yet).
Generate the help and context map first with `make help` on the host.

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

`make release` automatically downloads DOS ARJ, Info-ZIP Zip/UnZip, ACE,
RAR/UnRAR, Retro7Zip, LHA, ARC, PKARC/PKXARC and PKZIP/PKUNZIP, plus AUTOINS
and the OS/2 icons. [downloads.txt](downloads.txt) pins URLs and SHA-256
digests, following the `win3upd` download/cache model. Downloads stay in
`build/downloads` (`PACKER_CACHE=` overrides this); the downloaded files are excluded from Git. `curl`, `7z` and Python 3 are needed to download
and extract the upstream packages. The EXEs are installed next to VC;
original documentation, licenses, source packages and shareware packages
are retained in `PACKDOC`. Setup requires acceptance of all bundled terms
in nine license dialogs, grouping related legacy licenses into one text.
`INSTALL /S` retains GDI's usual automatic acceptance behavior.

The 1.44 MB image made by `make disk` is the core Commander distribution,
without downloaded third-party packers. The full directory/ZIP release
includes the larger packer collection and corresponding source archives.

The repository contains text sources for its own binary assets. `make assets`
builds 15 character translation tables and the icon without binary inputs or
network access. HLP files are built from XML. See [assets/README.md](assets/README.md)
for formats, provenance and the three historical Unicode mapping overrides.

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

With a compatible Open386MAX MAXTEXT driver loaded, VC automatically
chooses its highest advertised text mode at startup (80x50, then 80x43,
then 80x25). Without the driver or if selection fails, normal BIOS display
support remains available. No driver is bundled or installed by VC.
The [MAXTEXT integration notes](docs/maxtext-integration.md) explain the
startup client and reproducible DOS tests.

## Help (F1)

4.99.09 has the help pages, the buffer and the calls of the help, but no
help viewer (`CALL Help` was commented out). `src/VCHELP.INC` adds one: it
reads `VC.HLP` (Norton Guides, as in 4.05) from the directory of the
Commander and shows the index or a topic in a dialog of 4.99 (scroll bar,
mouse; menu `[ Next ] [ Previous ] [ Index ] [ Cancel ]`). The help page
of the panel, dialog, viewer or editor selects the topic; `HelpMap` gives
the topic by stable XML ID for each help context. New pages cover archives,
Retro7Zip, menus, helpers, OS/2, installation, current options, long names
and building the help. 44 reference chapters have been revised for
4.99.10 in all five languages,
including replacements for the old VCSETUP instructions. Unfinished menu
actions are identified in the help. See [the reference audit](help/REFERENCE-AUDIT.md).

`make help` compiles `help/src/*.xml` using our own Python compiler into
five DOS HLP files and an assembly context map under `build/help`.
`make release` includes these generated files. XMLmind can use the supplied
DTD and stylesheet to edit the sources. See [help/README.md](help/README.md)
for source elements, limits, imports and a 5.0 help preview. The current
program version remains 4.99.10 alpha.

Tests cover the original text imports, generated offsets, encodings,
record limits, context mapping, XML formatting and version substitution.
The native DOS smoke test also exercises the F1 index, new chapters,
Next and context help using the installed language.

## License

BSD 2-clause license (`LICENSE`, also `src/LICENSE.TXT`): the Volkov
Commander, and the changes and tools of this repository.

## Small extensions

F2, then F3 ("Erweiterungen...") opens the new ZIP, ARJ, ACE and file-list
menus, plus Retro7Zip, RAR, LHA, ARC, PKZIP and OS/2 helpers. `make release`
fetches the original DOS packers and installs them next to VC. `VCTOOLS.EXE` provides
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
implementations of a subset of the old add-ons' functionality. Third-party
binary downloads are excluded from Git, with their own licenses retained
in the assembled release. NTFS/LFN drivers and old binary patches remain
outside the package. The small VCTOOLS ZIP reader supports classic ZIP;
Retro7Zip is available for its wider format support. `VC7Z.EXE` normalizes
its technical listings for VC, including solid archives. VC still uses
32-bit file-size fields. Retro7Zip needs a 386 or newer processor.
