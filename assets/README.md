# Zeichentabellen und Icon aus Textquellen

`make assets` erzeugt die 15 `.TBL`-Dateien und `VC.ICO` unter
`build/assets/`. `make release` und `make disk` übernehmen diese Ausgaben.
Es werden keine alten Binärdateien oder Downloads zum Erzeugen benötigt.
Python 3 mit Standardbibliothek genügt.

Die Zeichentabellen heißen bei VC **TBL**, nicht CPL. Der Leser steht in
`src/VCFIND.INC` (`TableSelect`, `TableFill`, `TransSBCS`, `TransDBCS`).
Die Dateien sind keine ausführbaren Systemsteuerungs-Erweiterungen.

## Zeichentabellen bearbeiten

`charsets.xml` enthält Titel, Dateiname, DOS-Codepage und Zuordnungen.
`charsets.dtd` beschreibt die Struktur, auch für XMLmind. Eine TBL besteht aus:

- einem ASCII-Titel mit höchstens 60 Zeichen und CRLF;
- einem Typbyte: 0 für zwei Einbyte-Zuordnungstabellen, 1 für Unicode;
- genau 256 Byte Nutzdaten.

Bei Einbyte-Tabellen stehen zuerst 128 Zuordnungen von DOS-Bytes 80..FF
zum externen Zeichensatz, dann 128 Zuordnungen in Gegenrichtung. Jede
XML-Zeile nennt ihr erstes Eingabebyte und 16 hexadezimale Ausgabebytes.
Die ASCII-Hälfte wird vom Programm ergänzt. Bestehende Best-fit-Zuordnungen
und Nullwerte bleiben ausdrücklich in der Textquelle erhalten; sie lassen
sich nicht verlustfrei aus einem gewöhnlichen Unicode-Codec zurückrechnen.

Unicode-Tabellen enthalten 128 Little-Endian-Wörter für DOS-Bytes 80..FF.
Der Generator nutzt die Python-Codecs CP437, CP850, CP852 und CP866. Drei
historische Abweichungen sind als begründete `override`-Elemente sichtbar:

| Tabelle | Byte | Ausgabe |
|---|---|---|
| CP437 | E6 | U+03BC, griechisches Mu statt Mikrozeichen |
| CP850 | D5 | U+20AC, historische Euro-Variante statt punktlosem i |
| CP852 | AA | U+FFFF als historische Kennzeichnung ohne Zuordnung |

Dadurch bleibt das Verhalten der bisherigen Auslieferung erhalten.
Zuordnungen können gezielt geändert werden; die Tests melden Abweichungen
von den überprüften Original-Prüfsummen zur bewussten Prüfung.

Zum Benutzen eine Tabelle aus dem passenden CP-Verzeichnis ins VC-
Verzeichnis kopieren und im internen Betrachter mit F8 auswählen. Das
Dateiformat und seine ursprüngliche Verzeichnisstruktur bleiben erhalten.

## Icon bearbeiten

Die Quelle ist **`vc-icon.svg`**. Sie zeigt das originale 32×32-Pixelmotiv
als gültiges SVG mit Palette und Rechtecken. Die Klassen `c0` bis `cF`
legen die 16 Farben fest; Rechtecke mit `opacity="0"` sind transparent.
So lassen sich Farben und Pixel als Text oder im SVG-Editor ansehen.

Der kleine Compiler unterstützt dieses feste Pixel-Art-SVG-Format:
32×32, ganzzahlige untransformierte Rechtecke, vollständige Abdeckung ohne
Überlappung, 16 Palettenklassen und vollständige Deckung oder Transparenz.
Beliebige SVG-Pfade, Filter und Transformationen werden nicht stillschweigend
angenähert. Nach Bearbeitung durch einen Grafikeditor diese Struktur erhalten.

Erzeugt wird ein 16-Farben-ICO mit Windows-3.x-kompatibler Directory-/DIB-
Struktur, 4-Bit-Pixeln und separater AND-Transparenzmaske. Auch die unter
transparenten Pixeln gespeicherten Farbwerte bleiben nachvollziehbar.

## Herkunft und Prüfung

Die früher eingecheckten Tabellen und das Icon wurden gegen das
[Originalpaket vc49908a.zip](https://vc.vvv.kyiv.ua/download/vc49908a.zip)
verglichen: alle 16 Dateien waren identisch. Das heruntergeladene
Referenzpaket hat SHA-256:

```text
d64df4281aa6f2384688cc10da16ff7312ccae07ba998c0a3e2a0e832d225985
```

Archiv-URL, Archiv-Prüfsumme und jeweilige Original-Dateiprüfsumme stehen
in den XML-/SVG-Quellen. Die erzeugten Dateien waren anschließend ebenfalls
**bytegleich** mit allen 16 bisherigen Binärdateien. Diese alten Dateien
sind deshalb nicht mehr als Eingaben im Repository nötig.

`make test` prüft Ausgabeprüfsummen, Zuordnungen, Sonderfälle, Dateistruktur,
Icontransparenz und ungültige Quellen. `build/assets/manifest.xml` nennt die
aktuellen und ursprünglichen Prüfsummen. Optionale XML-Prüfung:

```sh
xmllint --noout --valid assets/charsets.xml
xmllint --noout assets/vc-icon.svg
```

Das Repository enthält für seine eigenen Artefakte nur Textquellen:
ASM/C, XML, SVG und die bisherigen Textdateien. Externe DOS-Packer und der
Installer bleiben separate, nachvollziehbare Build-/Download-Abhängigkeiten.
