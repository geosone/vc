# MAXTEXT in Volkov Commander: API- und Integrationsprüfung

Prüfstand: 24. Oktober 2026. VC `d571c4b479e254dee93b34fc9dff24711772daff`,
Open386MAX `05fe77dde1b21d8cef4ecf20403daf0816f82343` (9.00-beta4),
öffentliche MAXTEXT-API 1.1. Diese Datei beschreibt einen Einbauvorschlag.
VC enthält bisher keinen MAXTEXT-Client; der zugehörige DOS-Test untersucht
zunächst das unveränderte Programm mit dem externen Treiber.

## Ergebnis des Quellcodeabgleichs

MAXTEXT eignet sich als **optionales Backend für VGA-Textmoduswechsel**.
Es ist kein Hilfesystem, Schriftkonverter oder Ersatz für die VC-Oberfläche.
Die XML-Quellen und der HLP-Compiler benötigen dafür keine Formatänderung.
VC soll ohne Treiber weiter starten und seinen bisherigen BIOS-Pfad behalten.

Die aktuelle MAXTEXT-Version bietet 80×25, 80×43 und 80×50, abhängig von der
ermittelten Hardwareunterstützung. Sie bietet keine 132 Spalten, 60 Zeilen
oder VBE/SVGA-Modi. Der Treiber setzt DOS voraus, aber nicht den 386MAX-
Speichermanager. MAXTEXT selbst benötigt mindestens einen 286; das ist
keine neue Mindestanforderung für einen VC-Betrieb ohne diesen Treiber.

VC hat bereits eine brauchbare Grundlage:

| Stelle | Bestehendes Verhalten | Ansatz für MAXTEXT |
|---|---|---|
| `src/VCMENU.INC`, `F59_00` | Strg-F9 zählt BIOS-/VESA-Textmodi auf und setzt sie direkt mit INT 10h. | Zusätzliche Einträge aus dem validierten MAXTEXT-Modusbitmap anbieten. |
| `src/VCMENU.INC`, `ModeLine` | Ein Listeneintrag ist bisher eine BIOS-Modusnummer; zusätzliche Daten werden per VESA-Abfrage ermittelt. | Backend und Geometrie ausdrücklich mitführen; MAXTEXT-Einträge sind keine erfundenen VESA-Modusnummern. |
| `src/VCMENU.INC`, `F69_00` | Alt-F9 setzt den Modus direkt und lädt gegebenenfalls den 8-Pixel-Font. | Optional über denselben zentralen MAXTEXT-Wechselpfad führen. |
| `src/VCMENU.INC`, `F69_10` bis `F69_22` | Liest Modus/Font/Geometrie neu, prüft Platz, verschiebt Bildschirmpuffer, passt Maus/Prompt an und zeichnet Fenster. | Nach erfolgreichem Wechsel wiederverwenden; Hardware- und VC-Pufferzustand gemeinsam prüfen. |
| `src/VCMENU.INC`, `F69_30` / `F69_31` | Prüft die benötigten Bildschirmpuffer und den verbleibenden Arbeitsbereich. | Vor dem Wechsel zusätzlich den temporären MAXTEXT-Speicher berücksichtigen. |
| `src/VCSCREEN.INC`, `ScreenParms` | Berücksichtigt Bildschirmsegment und Offset der aktiven Seite; Adressierung nutzt `Columns`. | Diese Erkennung behalten. Ein MAXTEXT-Wechsel selbst ist nur auf Seite null erlaubt. |
| `src/VCOVL.ASM`, `Init40`–`Init60` | Erkennt beim Start Modus, Spalten, Zeilen und Zeichenhöhe über BIOS. | Vom Treiber gesetzte Geometrie kann bereits vor dem Start erkannt werden. |
| `src/VCOVL.ASM`, Speicherinitialisierung | VC reserviert einen großen DOS-Datenblock für seine eigenen Puffer. | Ein zusätzlicher DOS-48h-Aufruf während des Betriebs darf nicht als verfügbar vorausgesetzt werden. |
| `src/VCEXTMNU.INC`, `F32_32`; `src/VCOVL.ASM`, `RestoreMode` | Externe Aufrufe können eine Wiederherstellung der bisherigen Darstellung verlangen. | Einen absichtlichen Moduswechsel von einem normalen Kindprogramm unterscheiden. |
| `src/VCMENU.INC`, `F69_40` | Rekonstruiert den vorherigen Zustand aus BIOS-Modus und Font-Höhe. | Zeilenzahl zusätzlich speichern: 43 und 50 Zeilen können beide Modus 3 mit 8-Pixel-Font sein. |

Der bestehende Strg-F9-Pfad zeigt seine Liste erst nach erfolgreicher
VESA-Erweiterung an. MAXTEXT-Einträge müssen deshalb auch ohne VESA
angeboten werden können. Eine zusätzliche Abfrage allein vor der alten
VESA-Liste reicht nicht.

## Öffentliche DOS-API

Die Prüfung basiert auf `docs/maxtext.md`, `INC/MAXTEXT.INC`,
`INCLUDE/MAXTEXT.H`, `MAXTEXT/MTEXTCOM.ASM`, `MAXTEXT/MTEXAPI.C` und dem
Treiber in Open386MAX. Für VC kann ein kleiner eigener Assembler-Client
gegen das dokumentierte Protokoll geschrieben werden.

1. `MAXTEXT$` mit INT 21h, AX=3D02h öffnen.
2. AX=4400h prüft, ob der Handle ein Gerät bezeichnet. So wird eine
   gewöhnliche Datei mit diesem Namen nicht für den Treiber gehalten.
3. AX=4402h liest den 24-Byte-Status. Carry, Rückgabelänge, Signatur
   `MXT1`, ABI-Version und Strukturgröße prüfen.
4. Nur bekannte Fähigkeiten verwenden. ABI 1.0 genügt nicht zum Setzen;
   für Steuerbefehle ist mindestens die kompatible Version 1.1 nötig.
5. AX=4403h sendet ein 16-Byte-Steuerpaket. Erfolg verlangt Carry frei,
   AX=16 und Ergebniscode null. Anschließend Status und tatsächliche
   Geometrie erneut prüfen.
6. Handle und temporären Speicher auf allen Ausgangspfaden freigeben.

| Statusoffset | Inhalt |
|---|---|
| 00h | Signatur `MXT1`, vier Byte |
| 04h / 06h | ABI-Version / Strukturgröße, je ein Word |
| 08h | Diagnoseflags; kein Modusbitmap |
| 0Ah / 0Bh | BIOS-Modus / aktive Seite, je ein Byte |
| 0Ch / 0Eh / 10h | Spalten / Zeilen / Zeichenhöhe, je ein Word |
| 12h / 14h | residentes Segment / residente Bytezahl |
| 16h | Modusbitmap: 1=80×25, 2=80×43, 4=80×50 |

Das Steuerpaket enthält `MXTC`, Befehl, Spalten, Zeilen,
Scratch-Segment, Scratch-Größe in Paragraphen und Ergebniscode.
Befehl 1 setzt die gewünschte Geometrie. Befehl 2 stellt die Geometrie
beim Laden des Treibers wieder her. **RESTORE bedeutet nicht den Zustand
beim Start von VC**; für diesen Zweck die gespeicherte Geometrie mit SET
anfordern. Erfolgreiche Wechsel löschen den Bildschirm.

Der Treiber verlangt **1A00h Paragraphen = 104 KiB temporären konventionellen
Speicher**, beginnend am Offset null des übergebenen Segments. Gesichert
werden Textspeicher, Font-Ebene und BIOS-Zustand. Er darf weder Gerät noch
Steuerpaket überlappen und muss vollständig unterhalb A000h liegen.

VCs `AllocateBlock` nimmt eine Bytezahl in einem 16-Bit-Register entgegen;
104 KiB lassen sich darüber nicht in einem Aufruf reservieren. Für einen
internen Client muss nach Komprimierung/Prüfung des Arbeitsbereichs ein
zusammenhängender Bereich in Paragraphen reserviert werden. Während des
IOCTL-Aufrufs dürfen Puffer oder Segmentpositionen nicht verschoben werden.
Nach dem Aufruf den Bereich freigeben, bevor die Bildschirmverwaltung ihre
Puffer neu ordnet. Ein extern gestartetes MAXTEXT.COM allokiert dagegen
selbst; das beseitigt nicht automatisch die VC-Wiederherstellungsfrage.

Die Ergebniswerte unterscheiden nicht unterstützten Modus, ungültigen
Scratch-Bereich, unzulässigen Kontext, fehlgeschlagenen Wechsel mit
vollständiger Rücknahme und fehlgeschlagene Rücknahme. Ein Gerätefehler
oder abgelehnter Kontext darf nicht anschließend ungefragt durch einen
BIOS-Wechsel umgangen werden.

## Vorgeschlagener Einbau

Als erste Stufe bietet sich ein optionales F2-Untermenü an, das ein
vorhandenes `MAXTEXT.COM` für Status und die drei Modi aufruft. VC muss
dafür keinen Treiber installieren und keine neue Speicherreservierung
implementieren. Das ist ein eigener, kleinerer Integrationsschritt;
die folgende native API-Anbindung erweitert anschließend Strg-F9.

1. Eigenes `src/VCMAXTXT.INC` für Erkennung, Statusprüfung und gekapselten
   Steueraufruf. Kein zusätzliches TSR. Ohne Gerät bleibt der normale
   BIOS-Betrieb verfügbar. Die Erkennung selbst ändert keinen Modus.
2. Strg-F9 erhält die erkannten MAXTEXT-Modi mit Backend-Kennzeichnung.
   Ein Eintrag trägt mindestens Backend, Spalten und Zeilen. VESA-
   Abfragen werden nur für VESA-Einträge ausgeführt. Die erste Stufe
   bietet ausschließlich die aktuelle 80-Spalten-Familie an.
3. Ein zentraler Wechselpfad prüft Arbeitsspeicher und Pufferbedarf,
   sichert die gewünschte Rückkehrgeometrie, verbirgt den Mauszeiger,
   führt den API-Aufruf aus und prüft das Ergebnis. Danach folgt die
   vorhandene VC-Geometrie-/Pufferanpassung mit vollständigem Neuzeichnen.
4. Kindprogramme dürfen weiterhin ihren Modus ändern. Nach ihrer Rückkehr
   die tatsächliche Geometrie erneut feststellen. Die Rückkehrpolitik muss
   25/43/50 unterscheiden und darf einen ausdrücklich angeforderten neuen
   VC-Modus nicht versehentlich durch die alte Geometrie ersetzen.
5. Erst nach diesen Prüfungen die Auswahl persistent speichern. Die
   VC.INI ist keine beliebig erweiterbare Textdatei; ihr vorhandenes
   Versions-/Layoutverfahren muss berücksichtigt werden. Fehlendes MAXTEXT
   beim nächsten Start darf keinen Startabbruch bewirken.
6. Die aktuellen XML-Hilfethemen `panels` und `legacy_34` in allen fünf
   Sprachen um Bedienung und Grenzen ergänzen. In der Oberfläche genügt
   eine verständliche Modus-/Treiberanzeige; API-Details gehören hierher.

MAXTEXT verweigert Wechsel, während Windows den Bildschirm besitzt, in
Grafikmodi, auf anderen aktiven Seiten und bei nicht unterstützten nativen
Layouts. Das muss die Integration respektieren. Vorhandene BIOS- oder
VESA-Modi sind nicht automatisch vom MAXTEXT-Backend unterstützt.

Die Open386MAX-Implementierung, API-Header und Beispiele tragen
GPL-3.0-only. Der Vorschlag sieht einen eigenen Client anhand der
Protokollbeschreibung vor; Treiber und Originalheader werden hier weder
übernommen noch ins VC-Programm gelinkt. Ein späteres Mitliefern des
externen Treibers wäre eine zusätzliche Release-/Quellpaketaufgabe.

## Reproduzierbare Vorprüfung

`tests/dos_maxtext_probe.py` verwendet eine Kopie eines vorhandenen
DOS-Datenträgers und extern bereitgestellte MAXTEXT-Binärdateien:

```sh
make all help
python3 tests/dos_maxtext_probe.py \
  --image /pfad/zum/dos.img \
  --maxtext /pfad/zu/Open386MAX/build/bin \
  --output build/maxtext-probe
```

Standard-Partitionsoffset: 32256 Byte (`--offset` überschreibt ihn).
Der Test erstellt einen Lauf ohne Treiber und je einen Start mit
80×25, 80×43 und 80×50. Er liest BIOS-Geometrie und die tatsächlich
sichtbaren Textzellen, prüft die unterste Tastenleiste, die F1-Hilfe und
General-Kontexthilfe und startet externe Stapeldateien für weitere Wechsel.
Der Test führt außerdem ein isoliertes VC.MNU mit drei MAXTEXT-Aufrufen
aus. `--rows 25` beschränkt einen Lauf auf den Start mit 25 Zeilen,
`--rows 0` auf den Vergleich ohne Treiber.
Die nach Rückkehr beobachtete Geometrie wird ausdrücklich protokolliert;
sie wird nicht mit dem vom Kindprogramm angeforderten Modus gleichgesetzt.

Unter jedem Lauf liegen Bildschirmausgaben, BDA-/Textspeicherabbilder und
ein Ergebnisbericht. `inputs.sha256` identifiziert die tatsächlich benutzten
VC- und MAXTEXT-Binärdateien. Die Tests verändern keine echten CONFIG.SYS-
Dateien und verteilen weder DOS noch den Treiber. Sie prüfen noch keinen
neuen internen API-Client und noch keine reale Grafikkarte, Windows-Sitzung,
386MAX-/UMB-Kombination oder Speicherknappheit.

Für den späteren Client zusätzlich erforderlich: fehlendes/falsches Gerät,
alte ABI, beschädigte Antwort, unbekannte Bitmap-Bits, fehlender
zusammenhängender Scratch-Speicher, abgelehnter Windows-/Seitenkontext,
Treiber-Rollback und Fehler während der anschließenden VC-Pufferanpassung.

Primärquelle: [Open386MAX MAXTEXT-Dokumentation](https://github.com/geosone/Open386MAX/blob/05fe77dde1b21d8cef4ecf20403daf0816f82343/docs/maxtext.md).

## Beobachtete Ergebnisse

QEMU/SeaBIOS, CPU 486, MS-DOS 7.1, ohne 386MAX-Speichermanager:

| Start | Fenster und unterste Tastenleiste | F1 und General-Hilfe | Externe Wechsel 25 / 43 / 50 |
|---|---|---|---|
| Ohne Treiber, 80×25 | bestanden | bestanden | kein Treiberaufruf |
| MAXTEXT 80×25 | bestanden | bestanden | neue Geometrie jeweils übernommen |
| MAXTEXT 80×43 | bestanden | bestanden | neue Geometrie jeweils übernommen |
| MAXTEXT 80×50 | bestanden | bestanden | neue Geometrie jeweils übernommen |

Die externen Wechsel wurden von der VC-Befehlszeile über DOS-Stapeldateien
angefordert. Sie belegen den beobachteten Aufrufweg; die
`RestoreMode`-Logik anderer Viewer-/Erweiterungsaufrufe bleibt gesondert
zu berücksichtigen. Die Quelldatei `F69_40` speichert keine eigenständige
Zeilenzahl und ist deshalb kein Nachweis einer exakten 43-Zeilen-
Wiederherstellung für sämtliche Kindprogramme.

Ergebnisdateien dieses Laufs: `build/maxtext-review3/`. Der ergänzende
Benutzermenü-Lauf unter `build/maxtext-menu-review/` hat alle drei Wechsel
über F2 bestanden: VC übernimmt jeweils 25, 43 beziehungsweise 50 Zeilen
und zeichnet die unterste Tastenleiste an der passenden Position.
Die Ergebnisse begründen die Integration; sie behaupten keine bereits
implementierte interne API-Unterstützung in VC.
