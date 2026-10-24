#!/usr/bin/env python3
"""Fetch pinned DOS archivers and stage their files for `make release`."""
import argparse
import hashlib
import io
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile


def manifest(path):
    result = {}
    names = set()
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 4:
            raise ValueError(f"{path}:{number}: expected id, SHA-256, URL, filename")
        key, digest, url, name = fields
        if (key in result or name in names or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not re.fullmatch(r"[A-Za-z0-9_.+-]+", name) or name in (".", "..")):
            raise ValueError(f"{path}:{number}: duplicate or invalid download")
        result[key] = (digest, url, name)
        names.add(name)
    return result


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fetch(spec, cache):
    digest, url, name = spec
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / name
    if dest.is_file() and sha256(dest) == digest:
        print(f"Verified cache: {name}", flush=True)
        return dest
    print(f"Downloading {name} ...", flush=True)
    with tempfile.NamedTemporaryFile(dir=cache, suffix=".part", delete=False) as f:
        part = Path(f.name)
    try:
        subprocess.run(["curl", "--fail", "--location", "--silent", "--show-error",
                        "--retry", "3", "--connect-timeout", "20", "--max-time", "180",
                        "--output", str(part), url], check=True)
        actual = sha256(part)
        if actual != digest:
            raise ValueError(f"{name}: SHA-256 mismatch: {actual}, expected {digest}")
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    return dest


def archive_member(archive, member):
    # Select only explicit file names; never unpack paths supplied by an archive.
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            return z.read(member)
    return subprocess.run(["7z", "e", "-so", str(archive), member],
                          check=True, capture_output=True).stdout


def install_ini(template, files, licenses=()):
    text = Path(template).read_bytes().decode("cp850").replace("\r\n", "\n")
    if text.count("[Files]\n") != 1:
        raise ValueError("installer template must have one [Files] section")
    if licenses:
        # GDI supports nine license dialogs. Related legacy licenses share one
        # complete text, so every bundled product's terms are displayed.
        if len(licenses) > 9:
            raise ValueError("GDI supports at most nine license dialogs")
        lines = ["License=" + ",".join(str(i) for i in range(1, len(licenses)+1))]
        lines.extend(f"License{i}={title}|{path.replace('/', chr(92))}"
                     for i, (title, path) in enumerate(licenses, 1))
        text = text.replace("License=Volkov Commander|LICENSE.TXT", "\n".join(lines))
    entries = "\n".join(name.replace("/", "\\") for name in sorted(files))
    text = text.replace("[Files]\n", "[Files]\n; Downloaded DOS archivers\n"
                        + entries + "\n; Commander files\n")
    return text.replace("\n", "\r\n").encode("cp850")


def stage(downloads, target, template, specs):
    files = set()

    def put(name, data):
        if name in files:
            raise ValueError(f"duplicate staged file: {name}")
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        files.add(name)

    def member(package, name, dest):
        put(dest, archive_member(downloads[package], name))

    member("arj", "ARJ.EXE", "ARJ.EXE")
    for name in ("README.TXT", "DOS.TXT", "HISTORY.TXT"):
        member("arj", name, "PACKDOC/ARJ/" + name)
    member("arj", "COPYING", "PACKDOC/ARJ/COPYING.TXT")
    put("PACKDOC/ARJ/SOURCE.TGZ", downloads["arjsrc"].read_bytes())

    # The 16-bit Info-ZIP executables are installed under the usual DOS names.
    for package, original, installed in (("zip", "zip16.exe", "ZIP.EXE"),
                                          ("unzip", "unzip16.exe", "UNZIP.EXE")):
        folder = "PACKDOC/" + package.upper() + "/"
        member(package, original, installed)
        for source, dest in (("LICENSE", "LICENSE.TXT"), ("README", "README.TXT"),
                             ("README.DOS", "README.DOS"), (package + ".txt", "MANUAL.TXT")):
            member(package, source, folder + dest)

    member("ace", "ACE.EXE", "ACE.EXE")
    # Keep the complete, unchanged shareware packages as well as ready-to-run EXEs.
    put("PACKDOC/ACE/PACKAGE.ZIP", downloads["ace"].read_bytes())
    for name in ("ACE.DOC", "LICENSE.DOC", "REGISTER.DOC", "REGISTER.FRM"):
        member("ace", name, "PACKDOC/ACE/" + name)

    member("rar", "RAR.EXE", "RAR.EXE")
    put("PACKDOC/RAR/PACKAGE.EXE", downloads["rar"].read_bytes())
    for name in ("LICENSE.TXT", "RAR.TXT", "README.TXT", "REGISTER.TXT"):
        member("rar", name, "PACKDOC/RAR/" + name)
    member("unrar", "unrar.exe", "UNRAR.EXE")
    member("unrar", "license.txt", "PACKDOC/UNRAR/LICENSE.TXT")

    member("lha", "LHA.EXE", "LHA.EXE")
    put("PACKDOC/LHA/PACKAGE.EXE", downloads["lha"].read_bytes())
    member("lha", "LHA213.DOC", "PACKDOC/LHA/LHA213.DOC")
    member("lha", "HISTORY.ENG", "PACKDOC/LHA/HISTORY.ENG")
    member("lha", "LHA.HLP", "PACKDOC/LHA/LHA.HLP")
    lha_doc = archive_member(downloads["lha"], "LHA213.DOC")
    start = lha_doc.index(b"4.  Our distribution Policy")
    end = lha_doc.index(b"\r\n5.", start)
    put("PACKDOC/LHA/LICENSE.TXT", lha_doc[start:end])

    for name in ("PKZIP.EXE", "PKUNZIP.EXE", "PKZIPFIX.EXE", "ZIP2EXE.EXE"):
        member("pkzip", name, name)
    put("PACKDOC/PKZIP/PACKAGE.EXE", downloads["pkzip"].read_bytes())
    for name in ("LICENSE.TXT", "README.TXT", "MANUAL.TXT", "ORDER.TXT"):
        member("pkzip", name, "PACKDOC/PKZIP/" + name)

    for name in ("PKARC.EXE", "PKXARC.EXE", "PKARCJR.EXE", "PKXARCJR.EXE"):
        member("pkarc", name, name)
    member("pkarc", "PK36.EXE", "PACKDOC/PKARC/PACKAGE.EXE")
    member("pkarc", "MANUAL.DOC", "PACKDOC/PKARC/MANUAL.DOC")
    member("pkarc", "README.DOC", "PACKDOC/PKARC/README.DOC")
    pkarc_doc = archive_member(downloads["pkarc"], "MANUAL.DOC")
    pkarc_license = pkarc_doc[pkarc_doc.index(b"Software License"):].split(b"\x1a")[0]
    put("PACKDOC/PKARC/LICENSE.TXT", pkarc_license)

    member("arc", "ARC.EXE", "ARC.EXE")
    for name in ("ARC.DOC", "ARC.TXT", "ARCORDER.TXT"):
        member("arc", name, "PACKDOC/ARC/" + name)
    put("PACKDOC/ARC/PACKAGE.ZIP", downloads["arc"].read_bytes())
    put("PACKDOC/ARC/ORIGINAL.EXE", downloads["arcorig"].read_bytes())
    arc_doc = archive_member(downloads["arc"], "ARC.DOC")
    # Copyright, limited license/warranty and the distribution conditions in
    # the Introduction; keep the complete manual next to this dialog text.
    arc_pages = arc_doc.split(b"\x0c")
    if b"LIMITED LICENSE" not in arc_pages[1] or b"INTRODUCTION" not in arc_pages[4]:
        raise ValueError("ARC manual layout changed; review the license extraction")
    arc_license = b"\r\n".join(arc_pages[i] for i in (0, 1, 4, 5))
    put("PACKDOC/ARC/LICENSE.TXT", arc_license)

    member("autoins", "AUTOINS.COM", "AUTOINS.COM")
    put("PACKDOC/OS2/AUTOINS.ZIP", downloads["autoins"].read_bytes())
    for package, names in (("os2icons", ("VC-WN.ICO", "VC-FS.ICO")),
                            ("os2icons2", ("VC.ICO", "VCOS2.ICO"))):
        for name in names:
            member(package, name, "OS2/" + name)
        put("PACKDOC/OS2/" + specs[package][2].upper(), downloads[package].read_bytes())

    for name in ("7ZA.EXE", "7ZR.EXE", "7ZM.EXE", "7ZDEC.EXE"):
        member("retro7zip", "BIN/" + name, name)
    member("retro7zip", "README.TXT", "PACKDOC/7ZIP/README.TXT")
    source = archive_member(downloads["retro7zip"], "SOURCE/7ZIP.ZIP")
    put("PACKDOC/7ZIP/SOURCE.ZIP", source)
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        for original, name in (("COPYRIGHT.txt", "COPYRIGH.TXT"),
                               ("DOC/License.txt", "LICENSE.TXT"),
                               ("DOC/copying.txt", "COPYING.TXT"),
                               ("DOC/unRarLicense.txt", "UNRAR.TXT")):
            put("PACKDOC/7ZIP/" + name, z.read(original))

    def join_license(name, parts):
        content = b""
        for title, data in parts:
            content += title.encode("ascii") + b"\r\n" + b"=" * len(title) + b"\r\n\r\n"
            content += data.replace(b"\x1a", b"") + b"\r\n\r\n"
        put(name, content)

    join_license("PACKDOC/ZIP/TERMS.TXT", [
        ("Info-ZIP Zip 3.00", archive_member(downloads["zip"], "LICENSE")),
        ("Info-ZIP UnZip 6.00", archive_member(downloads["unzip"], "LICENSE"))])
    with zipfile.ZipFile(io.BytesIO(source)) as z:
        join_license("PACKDOC/7ZIP/TERMS.TXT", [
            ("Retro7Zip / 7-Zip", z.read("DOC/License.txt")),
            ("GNU Lesser General Public License", z.read("DOC/copying.txt")),
            ("UnRAR restriction", z.read("DOC/unRarLicense.txt"))])
    join_license("PACKDOC/LEGACY/TERMS.TXT", [
        ("PKZIP 2.50", archive_member(downloads["pkzip"], "LICENSE.TXT")),
        ("PKZIP shareware distribution", archive_member(downloads["pkzip"], "README.TXT")),
        ("PKARC / PKXARC 3.6", pkarc_license),
        ("ARC 6.02", arc_license)])

    lines = ["DOS archivers downloaded by make release", "",
             "ARJ 2.78 Open-Source; corresponding source: PACKDOC\\ARJ\\SOURCE.TGZ",
             "Info-ZIP Zip 3.00 / UnZip 6.00: 16-bit ZIP.EXE / UNZIP.EXE",
             "ACE 1.2b: unregistered shareware, 30-day evaluation",
             "RAR 2.06: unregistered shareware, 40-day evaluation (creates RAR2)",
             "UnRAR 3.80 beta: DOS32 extraction only (no RAR5 support)",
             "Retro7Zip 24.09+5: DOS, 386+, modern formats incl. RAR5 extraction",
             "LHA 2.13: copyright Haruyasu Yoshizaki; freeware with original documentation",
             "PKZIP/PKUNZIP 2.50, PKARC/PKXARC 3.6, ARC 6.02: original shareware",
             "AUTOINS: Ins-key autorepeat in OS/2 DOS sessions; run once per session",
             "OS/2 icons in OS2\\: VC-WN.ICO (window), VC-FS.ICO (full screen)",
             "", "Licenses, original documentation and shareware packages: PACKDOC\\",
             "These third-party files are not covered by the Commander's BSD license.",
             "7-Zip corresponding source: PACKDOC\\7ZIP\\SOURCE.ZIP", "",
             "Pinned downloads (SHA-256 verified before use):"]
    for key, (digest, url, name) in specs.items():
        lines.extend([key + ": " + name, digest, url, ""])
    put("PACKERS.TXT", "\r\n".join(lines).encode("ascii"))
    licenses = [
        ("Volkov Commander", "LICENSE.TXT"),
        ("ARJ Open-Source", "PACKDOC/ARJ/COPYING.TXT"),
        ("Info-ZIP Zip / UnZip", "PACKDOC/ZIP/TERMS.TXT"),
        ("ACE 1.2b shareware", "PACKDOC/ACE/LICENSE.DOC"),
        ("RAR 2.06 shareware", "PACKDOC/RAR/LICENSE.TXT"),
        ("UnRAR", "PACKDOC/UNRAR/LICENSE.TXT"),
        ("Retro7Zip / 7-Zip", "PACKDOC/7ZIP/TERMS.TXT"),
        ("LHA", "PACKDOC/LHA/LICENSE.TXT"),
        ("PKZIP / PKARC / ARC", "PACKDOC/LEGACY/TERMS.TXT")]
    (target / "INSTALL.INI").write_bytes(install_ini(template, files, licenses))
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("downloads.txt"))
    parser.add_argument("--cache", type=Path, default=Path("build/downloads"))
    parser.add_argument("--output", type=Path, default=Path("build/packers"))
    parser.add_argument("--installer", type=Path, default=Path("install/INSTALL.INI"))
    args = parser.parse_args()
    specs = manifest(args.manifest)
    downloads = {key: fetch(value, args.cache) for key, value in specs.items()}
    # Stage completely before replacing an earlier successful result.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent, prefix="packers-") as tmp:
        target = Path(tmp) / "files"
        target.mkdir()
        stage(downloads, target, args.installer, specs)
        if args.output.exists():
            shutil.rmtree(args.output)
        target.rename(args.output)


if __name__ == "__main__":
    main()
