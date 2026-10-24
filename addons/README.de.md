# Eigene kleine Erweiterungen für Volkov Commander

Diese Erweiterungen sind neu geschrieben und unter BSD-2-Clause verfügbar.
Es wurde kein Code aus Heikos Plug-In, PACKMENU, LISTER, Small Executor,
DET oder LGFV übernommen. `make release` lädt die unten genannten originalen
Packprogramme und OS/2-Helfer zusätzlich herunter; ihre Dateien bleiben im
Build-Verzeichnis und werden nicht in Git eingecheckt.

Im F2-Menü öffnet **F3 „Erweiterungen…“** die Erweiterungen. Dort stehen
eigene Untermenüs für ZIP, ARJ, ACE, Retro7Zip, RAR, LHA, ARC, PKZIP,
OS/2-Helfer und Dateilisten zur Verfügung.
Menüs und Quellcode können frei angepasst werden.

## Archivmenüs

ZIP, ARJ und ACE haben jeweils Einträge zum Erstellen/Erweitern, Auflisten,
Prüfen und Entpacken. Beim Erstellen werden die markierten Dateien über
eine temporäre Dateiliste von VC übergeben. Ohne Markierung verwendet VC
die aktuelle Datei. Entpackt wird in das Verzeichnis des anderen Fensters.

`make release` lädt die **DOS-Versionen** automatisch herunter, prüft ihre
SHA-256-Summen und legt die ausführbaren Programme direkt neben VC ab.
Die Menüs verwenden diesen Installationspfad und benötigen keinen
zusätzlichen PATH-Eintrag. Rückfragen zum Überschreiben bleiben aktiv. Info-ZIP erwartet für
UTC-Zeitstempel eine passende DOS-Umgebungsvariable `TZ`; ohne sie kann
es eine Warnung und Rückgabecode 1 liefern. Das separate PKZIP-Menü
verwendet die originale PKWARE-Ausgabe.

| Programme im VC-Ordner | Ausgabe und Aufgabe |
|---|---|
| ARJ.EXE | ARJ 2.78 Open-Source: erstellen, auflisten, prüfen, entpacken |
| ZIP.EXE / UNZIP.EXE | Info-ZIP 3.00 / 6.00, 16-Bit-DOS; ZIP-Menü |
| ACE.EXE | ACE 1.2b für DOS; Shareware, 30 Tage Testzeit |
| RAR.EXE | RAR 2.06 für DOS; erstellt alte RAR-Archive; 40 Tage Testzeit |
| UNRAR.EXE | UnRAR 3.80 beta für DOS32; entpackt alte RAR-Formate, kein RAR5 |
| 7ZA.EXE / 7ZR.EXE / 7ZM.EXE / 7ZDEC.EXE | Retro7Zip 24.09+5 für DOS, 386 oder neuer |
| LHA.EXE | LHA 2.13 von Haruyasu Yoshizaki, freie Weitergabe mit Dokumentation |
| ARC.EXE | ARC 6.02, historische Shareware |
| PKARC.EXE / PKXARC.EXE | PKARC/PKXARC 3.6; zusätzlich speichersparende JR-Ausgaben |
| PKZIP.EXE / PKUNZIP.EXE | Originale PKZIP/PKUNZIP-2.50-Shareware; separates PKZIP-Menü |

Die originalen Anleitungen, Lizenztexte, Shareware-Pakete und nötigen
Quellpakete liegen unter `PACKDOC`. Der Installer zeigt die Lizenzen vor
dem Kopieren zur Bestätigung an: neun Dialoge, mit zusammengefassten
Texten für Info-ZIP und die alten ARC-/PKWARE-Werkzeuge. Alle angezeigten
Lizenzen müssen akzeptiert werden. `INSTALL /S` akzeptiert sie wie bei
GDI üblich automatisch; der interaktive Aufruf fragt ausdrücklich nach.
Die Fremdprogramme behalten ihre eigenen Lizenzen und Testfristen.

Quellen, Versionsstände und Prüfsummen stehen in `downloads.txt`; die
Release enthält dieselben Angaben als `PACKERS.TXT`. Downloads landen in
`build/downloads`, ein weiterer Lauf prüft und verwendet den Cache.
`make release PACKER_CACHE=/anderer/cache` verwendet einen anderen Cache.

OldOS liefert die historischen PKZIP-, PKARC-, RAR- und LHA-Pakete.
Bei LHA ist dort der Link mit `.zip` falsch; verwendet wird die vorhandene
`.exe`. Der ARC-Selbstentpacker von OldOS scheitert an seiner eigenen
Integritätsprüfung; deshalb stammen die fertigen ARC-6.02-Dateien aus
einer ebenfalls fest geprüften ZIP-Ausgabe. Das OldOS-Original liegt
unverändert als `PACKDOC/ARC/ORIGINAL.EXE` bei.

## Retro7Zip im Archivfenster

`VCARCH.EXT` verwendet Retro7Zip für 7z, XZ, BZip2, gzip, TAR, moderne
RAR-Dateien einschließlich RAR5 sowie viele lesbare Container wie CAB,
ISO, WIM und Datenträgerabbilder. Die erreichbaren Formate zeigt `7ZA i`.
Erstellen und Ändern stehen nur für Formate zur Verfügung, die das
jeweilige Packprogramm schreiben kann. RAR.EXE erzeugt RAR2; Retro7Zip
erzeugt keine RAR-Archive. TGZ/TBZ/TXZ sind verschachtelte Archive:
zuerst die Kompressionsschicht, dann die enthaltene TAR-Datei öffnen.

`VC7Z.EXE` übersetzt technische 7-Zip-Listen in ein stabiles Format für
VC. Das funktioniert auch mit Solid-Archiven, deren einzelne Dateien
keine eigene komprimierte Größe besitzen. Dort zeigt VC für diese
Größe 0; Dateiname und ursprüngliche Größe bleiben erhalten. Fehlende
Zeitstempel werden als 01.01.1980 dargestellt. Größen über 32 Bit werden
abgewiesen, weil die Dateiverwaltung von VC solche Werte nicht abbildet.

Zum Entpacken ins andere Fenster wechselt VC7Z zunächst in den Zielordner.
Das umgeht einen Fehler der DOS-Ausgabe von Retro7Zip beim direkten
Angeben eines bereits vorhandenen Ausgabeordners. Laufwerkswechsel
werden dabei berücksichtigt. Die 7-Zip-Varianten benötigen einen 386;
7ZM ist die kleine Variante für einfache 7z-Archive und wenig Speicher,
7ZA deckt die größte Formatauswahl ab. Speicherbedarf und mögliche
Dateigrößen bleiben durch DOS und die jeweilige Kompression begrenzt.

## OS/2-Helfer

`AUTOINS.COM` stammt unverändert aus dem VC-Downloadbereich und ermöglicht
die Wiederholung der Einfügen-Taste in einer DOS-Sitzung unter OS/2.
Im OS/2-Untermenü kann es einmal je Sitzung gestartet werden; der Installer
lädt es nicht automatisch. Unter `OS2` liegen die originalen Symbole für
Fenster- und Vollbildsitzungen (`VC-WN.ICO`, `VC-FS.ICO`) und weitere
OS/2-Symbole. Die zugehörigen Original-ZIPs liegen unter `PACKDOC/OS2`.
Das sind Helfer für die DOS-Ausgabe von VC, keine nativen OS/2-Packer.

**ZIP-Inhaltslisten** erzeugt unser `VCTOOLS.EXE` selbst und ohne Packprogramm.
Unterstützt werden klassische ZIP-Dateien mit einem Datenträger, einschließlich
Deflate und anderer Kompressionsmethoden, weil nur das Inhaltsverzeichnis
gelesen wird. Es wird nichts entpackt und keine CRC-Prüfung vorgenommen.
ZIP64 und mehrteilige ZIP-Dateien werden mit einer Fehlermeldung abgewiesen.
Dateinamen werden als gespeicherte Bytes ausgegeben; UTF-8 wird unter DOS
nicht in die Bildschirm-Codepage umgerechnet. Selbstentpackende ZIP-Dateien
mit vorangestelltem Programmcode können ebenfalls aufgelistet werden.

## Dateilisten und Stapelbefehle

Das Untermenü „Dateilisten und Stapelbefehle“ bietet:

| Taste | Funktion |
|---|---|
| N | Kurze Dateinamen nach `VC.LST` schreiben |
| L | Die von VC gelieferten langen Namen nach `VCLONG.LST` schreiben |
| P | Vollständige kurze Pfade nach `VCPATH.LST` schreiben |
| B | Eine einfache Batchdatei mit `ECHO` je Datei erzeugen: `VCLIST.BAT` |
| D | Einen Befehl je markierter Datei als Vorschau anzeigen |
| R | Einen Befehl je markierter Datei ausführen |

**Die vier Ausgabedateien werden im aktiven Verzeichnis überschrieben.**
Unterverzeichnisse werden dabei so übernommen, wie VC sie in seine Liste
schreibt; VCTOOLS führt keine zusätzliche rekursive Suche aus.

Im Befehl steht `{}` für den Dateinamen, beispielsweise `ATTRIB +R {}`.
VCTOOLS setzt jeden eingesetzten Namen in Anführungszeichen. Eine Vorschau
führt nichts aus. Bei einem Fehler endet die Verarbeitung; vorher erfolgreich
ausgeführte Befehle werden nicht rückgängig gemacht. DOS erlaubt nur kurze
Befehlszeilen: nach der Ersetzung sind höchstens 126 Bytes zulässig. Namen
mit Shell-Steuerzeichen werden abgewiesen. Der eingegebene Befehl selbst ist
ein normaler Shell-Befehl und wird entsprechend ausgeführt.

Die Verarbeitung erfolgt zeilenweise. Eine überlange Listenzeile wird als
Fehler behandelt, statt abgeschnitten als anderer Dateiname verarbeitet zu
werden. Relative Namen beziehen sich auf das aktuelle Arbeitsverzeichnis.
DOS-Dateizugriffe des Helfers verwenden 8.3-Namen; deshalb verwenden die
Menüs dafür `!~.!` und `!~@`. Eine Textliste langer Namen kann auch ohne
LFN-Treiber ausgegeben werden; ihre Erzeugung hängt von VC/DOSLFN ab.

## Formaterkennung und Hexansicht

`T` erkennt anhand des Dateianfangs ZIP, ARJ, RAR, ACE, LHA/LZH, 7-Zip,
gzip, CAB, TAR, MZ, ELF, PDF, GIF, PNG, JPEG, BMP und WAV. Hinzu kommen
leere Dateien und eine einfache Text-Heuristik für die ersten 512 Bytes.
Die Erkennung ist ein Hinweis auf die Signatur, keine Prüfung der Datei.
Eingebettete Archive in EXE-Dateien werden als MZ-Programm erkannt.

`H` gibt die ersten 256 Bytes als Hex- und ASCII-Tabelle aus. Auf der
Befehlszeile lassen sich Anfang und Länge angeben. Dies ist eine kleine
Leseansicht, kein vollständiger Hiew-Ersatz mit Editor oder Disassembler.

## Befehlszeile

```text
VCTOOLS list LISTE [--full] [PRAEFIX [SUFFIX]]
VCTOOLS run LISTE "BEFEHL {}" [--dry-run]
VCTOOLS type DATEI
VCTOOLS zip ARCHIV
VCTOOLS hex DATEI [OFFSET [LAENGE]]
```

Alle Listen und Ansichten gehen auf die Standardausgabe und lassen sich
mit `>` in eine Datei umleiten. Zahlen für die Hexansicht sind dezimal
oder mit `0x` hexadezimal; eine führende Null bedeutet oktal.

`!$` bzw. `%$` ist eine neue VC-Menüvariable: das Installationsverzeichnis
von VC mit abschließendem Backslash. Die Menüs können dadurch VCTOOLS
finden, auch wenn VC nicht im `PATH` steht und ein anderes Verzeichnis
angezeigt wird. Bereits vorhandene Menüs werden beim Update durch den
Installer erhalten; dort muss `addons.mnu` gegebenenfalls von Hand als
Untermenü ergänzt werden. Die neuen Untermenüs werden regulär installiert.

## Welche alten Downloads werden ersetzt?

| Historische Erweiterung | Stand in diesem Repo |
|---|---|
| Heikos Archivmenüs, PACKMENU | Eigene Archivmenüs; DOS-Packer lädt `make release` herunter |
| Heikos Dateilisten-Helfer, LISTER, Small Executor | Eigene Listen, Präfix/Suffix, volle kurze Pfade und Stapelbefehle |
| DET | Eigene, kleinere Signaturerkennung |
| LGFV / ARCVIEW | Eigene ZIP-Inhaltsanzeige; andere Archive über externe Packer |
| FILES_NC / RESINFO | VC 4.99 zeigt bereits Dateibeschreibungen an; kein neuer TSR |
| VC Enhancer / Preprocessor | Vorhandene VC-4.99-Variablen für beide Fenster, ergänzt um `!$` |
| VC-COLOR | Farben lassen sich bereits im VC-Einstellungsmenü ändern |
| HA, Swift Editor, Hiew | Keine vollständigen neuen Packer, Editoren oder Disassembler |
| NTFS-Treiber und LFN-Treiber | Nicht Bestandteil; für lange Namen vorhandenes DOSLFN verwenden |
| OS/2-Helfer | Originales AUTOINS und OS/2-Symbole in der vollen Release |
| Patches für VC 4.0x | Nicht für diesen Build übernommen |

## Bauen und prüfen

`make addons` baut VCTOOLS und VC7Z als 16-Bit-DOS-EXE mit Open Watcom.
Voreinstellung: `WATCOM=/opt/watcom`, Compiler `binl64/wcl`; alternativ
`WATCOM=` und `WCL=` setzen. `make` und `make release` bauen beide mit.
Zum Herunterladen und Auspacken der Fremdpakete werden `curl`, `7z` und
Python 3 benötigt. Die 1,44-MB-Diskette (`make disk`) enthält nur VC und
die eigenen Helfer; die vollständige Sammlung mit Fremdprogrammen und
Quellpaketen ist deutlich größer und liegt in der ZIP-/Verzeichnis-Release.

`make test` baut denselben C89-Quellcode mit dem Host-C-Compiler und prüft
Dateilisten, Befehlsersetzung, Fehlerfälle, Formaterkennung, ZIP-Parser und
Hexausgabe. Der native DOS-Test läuft separat mit einer lokal vorhandenen,
DOS-bootfähigen Festplattenabbildung; siehe `tests/dos_smoke.py --help`.
Ein DOS-Abbild wird nicht mitgeliefert.
