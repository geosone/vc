# Eigene kleine Erweiterungen für Volkov Commander

Diese Erweiterungen sind neu geschrieben und unter BSD-2-Clause verfügbar.
Es wurde kein Code aus Heikos Plug-In, PACKMENU, LISTER, Small Executor,
DET oder LGFV übernommen. Die heruntergeladenen Programme unter `build/down/`
gehören nicht zur Veröffentlichung.

Im F2-Menü öffnet **F3 „Erweiterungen…“** die Erweiterungen. Dort stehen
eigene Untermenüs für ZIP, ARJ, ACE und Dateilisten zur Verfügung.
Menüs und Quellcode können frei angepasst werden.

## Archivmenüs

ZIP, ARJ und ACE haben jeweils Einträge zum Erstellen/Erweitern, Auflisten,
Prüfen und Entpacken. Beim Erstellen werden die markierten Dateien über
eine temporäre Dateiliste von VC übergeben. Ohne Markierung verwendet VC
die aktuelle Datei. Entpackt wird in das Verzeichnis des anderen Fensters.

Die Menüs benötigen die **DOS-Versionen** von PKZIP/PKUNZIP, ARJ bzw. ACE
im `PATH`. Diese Packprogramme werden nicht mitgeliefert und wurden nicht
nachgebaut. Das entspricht der Funktion der früheren Menü-Erweiterungen.
Einige neuere oder andere Ausgaben der Packprogramme haben andere Schalter;
die Menüdateien richten sich nach den DOS-Programmen der VC-4.99-Zeit.
Rückfragen zum Überschreiben bleiben beim jeweiligen Packprogramm aktiv.

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
| Heikos Archivmenüs, PACKMENU | Eigene ZIP-/ARJ-/ACE-Menüs; externe Packer erforderlich |
| Heikos Dateilisten-Helfer, LISTER, Small Executor | Eigene Listen, Präfix/Suffix, volle kurze Pfade und Stapelbefehle |
| DET | Eigene, kleinere Signaturerkennung |
| LGFV / ARCVIEW | Eigene ZIP-Inhaltsanzeige; andere Archive über externe Packer |
| FILES_NC / RESINFO | VC 4.99 zeigt bereits Dateibeschreibungen an; kein neuer TSR |
| VC Enhancer / Preprocessor | Vorhandene VC-4.99-Variablen für beide Fenster, ergänzt um `!$` |
| VC-COLOR | Farben lassen sich bereits im VC-Einstellungsmenü ändern |
| HA, Swift Editor, Hiew | Keine vollständigen neuen Packer, Editoren oder Disassembler |
| NTFS-Treiber und LFN-Treiber | Nicht Bestandteil; für lange Namen vorhandenes DOSLFN verwenden |
| OS/2-Helfer und Patches für VC 4.0x | Nicht für diesen Build übernommen |

## Bauen und prüfen

`make addons` baut VCTOOLS als 16-Bit-DOS-EXE für 8086 mit Open Watcom.
Voreinstellung: `WATCOM=/opt/watcom`, Compiler `binl64/wcl`; alternativ
`WATCOM=` und `WCL=` setzen. `make` und `make release` bauen es mit.

`make test` baut denselben C89-Quellcode mit dem Host-C-Compiler und prüft
Dateilisten, Befehlsersetzung, Fehlerfälle, Formaterkennung, ZIP-Parser und
Hexausgabe. Der native DOS-Test läuft separat mit einer lokal vorhandenen,
DOS-bootfähigen Festplattenabbildung; siehe `tests/dos_smoke.py --help`.
Ein DOS-Abbild wird nicht mitgeliefert.
