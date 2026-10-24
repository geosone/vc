# Optionale MAXTEXT-Unterstützung in VC

Stand: 25. Oktober 2026. Referenz für die API: Open386MAX
`05fe77dde1b21d8cef4ecf20403daf0816f82343` (9.00-beta4), API 1.1.

## Verhalten beim Start

VC erkennt beim ersten Start einen vorhandenen MAXTEXT-Treiber und wählt
automatisch dessen höchsten angebotenen Textmodus:

1. 80×50, wenn Bit 2 des Modusbitmaps gesetzt ist;
2. sonst 80×43, wenn Bit 1 gesetzt ist;
3. sonst 80×25, wenn Bit 0 gesetzt ist.

Unbekannte Bitmap-Bits werden nicht als zusätzliche Modi interpretiert.
Ist die gewünschte Zeilenzahl bereits aktiv, wird kein löschender
Moduswechsel ausgeführt. MAXTEXT bietet derzeit keine 132 Spalten,
60 Zeilen oder VBE/SVGA-Modi an.

**MAXTEXT ist optional.** Ohne Gerät, bei inkompatibler API, fehlerhafter
Antwort, fehlendem Start-Arbeitsbereich oder abgelehntem Wechsel läuft
VC mit seiner bisherigen Initialisierung weiter. Der Treiber wird weder
installiert noch mit VC mitgeliefert. Die normale BIOS-Anzeige bleibt
verfügbar. Nach einer Geräteablehnung versucht der neue Client keinen
zusätzlichen BIOS-Wechsel, der die Ablehnung umgehen würde.

Die automatische Auswahl erfolgt einmal pro VC-Start. Ein späterer
manueller Wechsel wird beim Zurückkehren aus einem Programm nicht erneut
durch die automatische Auswahl ersetzt. Alt-F9 und Strg-F9 verwenden
weiterhin ihre vorhandenen BIOS-/VESA-Pfade; sie sind noch keine nativen
MAXTEXT-Einstellungsdialoge. Die XML-Hilfe erklärt das aktuelle Verhalten
in den Themen `panels` und `legacy_34` in allen fünf Sprachen.

## Einbau und Speicher

`src/VCMAXTXT.INC` enthält einen eigenständig geschriebenen Assembler-
Client. `src/VC.ASM`, `Init20`, ruft ihn **vor dem Laden der Oberfläche**
auf. Danach ermittelt die bestehende Initialisierung die tatsächliche
BIOS-Geometrie und legt die VC-Bildschirmpuffer passend an. Deshalb muss
für diese Startfunktion kein laufender Dialog umgebaut werden.

MAXTEXT braucht für einen Wechsel 1A00h Paragraphen = 104 KiB temporären
konventionellen Speicher. Ein zusätzliches DOS-48h-Allocate während des
normalen VC-Betriebs wäre problematisch: VC nutzt einen großen eigenen
DOS-Datenblock. Der Startclient verwendet deshalb einen anderen Zeitpunkt:

- Der DOS-PSP von VC.COM besitzt bereits eine MCB-beschriebene
  Speicherzuweisung. Der Startstack liegt laut `Init01` innerhalb der
  ersten 64 KiB.
- Der Client prüft den MCB-Eigentümer, mindestens 2A00h Paragraphen
  zugewiesenen Speicher und ein Ende unterhalb beziehungsweise bei A000h.
- Nur dann verwendet er die **nächsten** 104 KiB nach den ersten 64 KiB
  vorübergehend als Scratch-Bereich. Code, Stack und API-Pakete bleiben
  außerhalb dieses Bereichs.
- Spätere Initialisierung darf diesen Bereich normal wiederverwenden.
  Es gibt keine zusätzliche DOS-Speicherzuweisung, Größenänderung,
  neue residente Komponente oder Änderung des VC.INI-Layouts.

Der Client verändert beim Rücksprung keine Register oder Flags des
Aufrufers. Der vorhandene 8086-Codepfad ohne MAXTEXT bleibt erhalten;
der externe MAXTEXT-Treiber selbst setzt mindestens einen 286 voraus.

## Verwendete öffentliche API

Die Implementierung beruht auf der Protokollbeschreibung, nicht auf
übernommenen GPL-Headern oder Treiberroutinen:

| Schritt | DOS-Aufruf und Prüfung |
|---|---|
| Öffnen | INT 21h, AX=3D02h, Gerätename `MAXTEXT$` |
| Gerät prüfen | AX=4400h; ein gewöhnlicher Dateihandle wird abgewiesen |
| Status lesen | AX=4402h, 24 Byte; Carry, Rückgabelänge, `MXT1`, Major 1, Minor mindestens 1 und Größe 24 prüfen |
| Modus wählen | Modusbitmap am Statusoffset 16h; nur bekannte Bits 1/2/4 verwenden |
| Wechsel | AX=4403h, 16-Byte-Paket `MXTC`, SET=1, 80 Spalten, Zielzeilen, Scratch-Segment, 1A00h Paragraphen |
| Ergebnis | Carry frei, AX=16 und Ergebnis null verlangen; danach Status erneut abfragen |
| Abschluss | Handle auf jedem Ausgangspfad schließen; normale VC-BIOS-Erkennung fortsetzen |

Die Diagnoseflags am Offset 08h sind **kein** Modusbitmap. Rohwerte für
BIOS-Modus, aktive Seite, Spalten, Zeilen und Zeichenhöhe stehen an den
Offsets 0Ah bis 10h. Der Client fordert Wechsel nur aus Farbtextmodus 3
mit 80 Spalten und Seite null an. Die eigentlichen Hardware- und
Kontextprüfungen übernimmt zusätzlich der Treiber.

MAXTEXT lehnt unter anderem Windows-Bildschirmbesitz, Grafikmodi,
andere aktive Seiten und nicht unterstützte native Layouts ab. Ein
BDA-Wert allein beweist keine Hardwarefähigkeit. Der Treiber sichert
Bildschirm, Fonts und BIOS-Zustand und unterscheidet fehlgeschlagenen
Wechsel mit Rücknahme von fehlgeschlagener Rücknahme.

Der alternative API-Befehl RESTORE bezeichnet die Geometrie beim Laden
des Treibers, nicht den Zustand beim Start von VC. Der Startclient
benutzt ihn nicht. Erfolgreiche SET-Wechsel löschen den Bildschirm.

## Tests

Der native Test verwendet ausschließlich Kopien eines extern bereitgestellten
DOS-Abbilds. MAXTEXT-Binärdateien bleiben ebenfalls externe Testeingaben:

```sh
make all help
python3 tests/dos_maxtext_probe.py \
  --image /pfad/zum/dos.img \
  --maxtext /pfad/zu/Open386MAX/build/bin \
  --auto --output build/maxtext-auto
```

Standard-Partitionsoffset: 32256 Byte (`--offset` überschreibt ihn).
`--rows 0` prüft nur ohne Treiber, `--rows 25` nur den Start mit vorher
gewählten 25 Zeilen. Ohne `--auto` erwartet der Test die vorher eingestellte
Geometrie und eignet sich zum Vergleich mit einem VC ohne Startclient.

QEMU/SeaBIOS, CPU 486, MS-DOS 7.1, ohne 386MAX-Speichermanager:

| Zustand vor VC-Start | Zustand nach automatischer Auswahl | F1 und General-Hilfe |
|---|---|---|
| Kein Treiber, 80×25 | 80×25 | bestanden |
| MAXTEXT, 80×25 | 80×50 | bestanden |
| MAXTEXT, 80×43 | 80×50 | bestanden |
| MAXTEXT, 80×50 | 80×50 | bestanden |

Danach werden Wechsel auf 25/43/50 Zeilen über DOS-Stapeldateien und ein
isoliertes F2-Benutzermenü geprüft. VC übernimmt jeweils die neue
Geometrie und zeichnet die unterste Tastenleiste passend. Insbesondere
wird ein manuell gewähltes 80×43 nicht wieder automatisch auf 80×50 gesetzt.
Die vorherige Kompatibilitätsprüfung ohne Startclient bleibt unter
`build/maxtext-review3/` und `build/maxtext-menu-review/` nachvollziehbar;
die Startauswahl wird unter `build/maxtext-auto/` protokolliert.

`--fault` lädt stattdessen das eigene, absichtlich unvollständige
Testgerät `tests/dos/MAXTFAKE.ASM`. Es ändert keinen Videomodus, zeichnet
Steueranforderungen auf und lehnt sie ab. Die Fälle umfassen alte/falsche
ABI, Signatur, Rückgabelänge, Strukturgröße, leeres/unbekanntes Bitmap,
einen nur 43 Zeilen anbietenden Treiber und abgelehnte Steueraufrufe.
Ein Fall legt stattdessen eine gewöhnliche Datei namens MAXTEXT$ an und
prüft, dass sie unverändert bleibt. Beispiel:

```sh
python3 tests/dos_maxtext_probe.py \
  --image /pfad/zum/dos.img --maxtext /pfad/zu/Open386MAX/build/bin \
  --fault only-43 --output build/maxtext-faults
```

Unter jedem Lauf liegen Bildschirm- und BDA-Abbilder sowie ein Bericht;
`inputs.sha256` identifiziert die benutzten Binärdateien. Das Testgerät
verlangt JWasm. DOS und Treiber werden nicht verteilt. Diese Tests sind
kein Nachweis für reale Grafikkarten, Windows-Sitzungen oder jede
386MAX-/UMB- und Speicherdruck-Kombination.

## Weitere mögliche Integration

Ein späterer manueller MAXTEXT-Dialog kann die geprüften Fähigkeiten in
Strg-F9 anbieten. Dafür müssen Einträge ein Backend und eine Geometrie
tragen: Die bisherige `ModeLine`-Routine interpretiert Einträge als
BIOS-/VESA-Modusnummern und darf MAXTEXT-Einträge nicht per VESA abfragen.
Die Liste muss auch ohne erfolgreiche VESA-Erweiterung angezeigt werden.

Für Wechsel während des Betriebs wären die Arbeitsbereichsreservierung
und `F69_10` bis `F69_22` für Puffer, Maus und Neuzeichnen zu verbinden.
VCs `AllocateBlock` akzeptiert eine 16-Bit-Bytezahl; 104 KiB sind darüber
nicht in einem Aufruf reservierbar. Die Wiederherstellung nach beliebigen
Viewer-/Erweiterungsaufrufen muss 25/43/50 unterscheiden: `F69_40` kennt
bislang BIOS-Modus und Font-Höhe, aber keine eigene gespeicherte Zeilenzahl.
Das ist von der implementierten automatischen Startauswahl getrennt.

Die Open386MAX-Implementierung, API-Header und Beispiele tragen
GPL-3.0-only. Der neue VC-Client ist eigener BSD-2-Clause-Code gegen die
öffentliche DOS-Schnittstelle. Ein späteres Mitliefern des externen
Treibers wäre eine zusätzliche Release-/Quellpaketaufgabe.

Primärquelle: [Open386MAX MAXTEXT-Dokumentation](https://github.com/geosone/Open386MAX/blob/05fe77dde1b21d8cef4ecf20403daf0816f82343/docs/maxtext.md).
