VC fonts: CP437, CP850, CP852 and CP866
====================================

Sources: Unscii by Viznut and contributors, base 8- and 16-pixel fonts.
https://github.com/viznut/unscii
Revision: 257b4dfeb50651510fe8b9cf4f151a148a4490e4
Original paths: fontfiles/unscii-8.hex and fontfiles/unscii-16.hex
The source checksums are pinned in tools/fonts.py and the build manifest.
The upstream README and its license statement are included as UNSCII.TXT.
Only the Public Domain / CC0 base fonts are used; no Unifont/GPL files.

Supplemental characters missing from these base fonts are original 8x8
pixel drawings in supplements.xml, dedicated to CC0-1.0 by Mario Fetka.
Their 8x16 versions repeat every scanline twice. No missing character is
silently replaced by a question mark. NUL is blank; bytes 1-31 and 127
use the IBM display pictures. The other slots follow assets/codepages.xml.

Build: make fonts (Python standard library, no network downloads).
Outputs: eight raw VGA fonts (256 characters, 8 or 16 bytes each) and
VC.CPI, a standard DOS FONT-format CPI with all four codepages and sizes.
CPI format reference: https://www.seasip.info/DOS/CPI/cpi.html
The CPI can be used with compatible DOS DISPLAY/MODE tools. Configure
those tools according to your DOS manual. VC itself uses the raw fonts.

Run VCFONT 437, 850, 852 or 866 to load the font matching the current
8- or 16-scanline VGA text mode, or VCFONT AUTO for the active DOS codepage.
VCFONT ROM restores the BIOS font for the current scanline height.
The F2 extensions menu offers these commands under S (screen fonts).
This changes display glyphs, not keyboard layout or DOS codepage settings.
It does not install a resident driver. MAXTEXT is optional. A later video
mode switch or program may replace the font; run VCFONT again afterward.
Unsupported hardware, graphics, Windows sessions or other font heights
are rejected before loading. In particular, 8x14/80x43 is not supported.

Raw font files must stay in the FONTS directory beside VCFONT.EXE.
Generated binaries belong in build/ and the release, not in Git.
