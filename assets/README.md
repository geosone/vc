# Zeichentabellen und Icon aus Textquellen

`make assets` erzeugt die 15 `.TBL`-Dateien und `VC.ICO` unter
`build/assets/`. `make release` und `make disk` übernehmen diese Ausgaben.
Es werden keine alten Binärdateien oder Downloads zum Erzeugen benötigt.
Python 3 mit Standardbibliothek genügt.

Die Zeichentabellen heißen bei VC **TBL**, nicht CPL. Der Leser steht in
`src/VCFIND.INC` (`TableSelect`, `TableFill`, `TransSBCS`, `TransDBCS`).
Die Dateien sind keine ausführbaren Systemsteuerungs-Erweiterungen.

## Zeichensätze und echte Generierung

Die TBL-Dateien enthalten **Zuordnungen von Zeichencodes, keine gezeichneten
Schriftzeichen**. Die Pixel eines sichtbaren Buchstabens kommen aus dem
BIOS-/DOS-Bildschirmfont. Ein Unicode-Codepoint alleine enthält keine
Buchstabenform.

`codepages.xml` beschreibt die Zeichenrepertoires mit Herkunftslinks.
Die Standardtabellen stammen aus den entsprechenden Python-Codecs;
Kamenický, Mazovia und CWI-2 werden als kleine, benannte nationale
Abweichungen von CP437 definiert. Ihre Zeichen haben Unicode-Wert,
lesbares Zeichen und Namen. Beide TBL-Richtungen werden daraus berechnet:

```text
Quellbyte -> Unicode-Zeichen -> Byte im Zielzeichensatz
```

Beispiel: CP1251-Byte C0 ist А (U+0410). In CP866 liegt dieses Zeichen
auf Byte 80. Es ist keine gespeicherte Ergebnis-Zeile nötig. Wird als
externer Zeichensatz KOI8-R gewählt, ergibt dieselbe Berechnung E1.
Die beiden Richtungen werden unabhängig berechnet, weil Ersatzzeichen
mehrdeutig sein können und eine angenäherte Tabelle nicht invertierbar ist.

| TBL / Definition | Ausgangsbasis und Quelle |
|---|---|
| CP437, CP850, CP852, CP866 | Microsofts DOS-Zuordnungen bei [Unicode.org](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/PC/) |
| CP1250, CP1251 | Microsofts Windows-Zuordnungen bei [Unicode.org](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/WINDOWS/) |
| ISO88592, ISO88595 | ISO-8859-2 / ISO-8859-5; [Unicode-Zuordnungen](https://www.unicode.org/Public/MAPPINGS/ISO8859/) |
| KOI8R | KOI8-R nach RFC 1489; [Unicode-Zuordnung](https://www.unicode.org/Public/MAPPINGS/VENDORS/MISC/KOI8-R.TXT) |
| MAC866 | Mac Cyrillic; [Apple-Zuordnung und Versionsgeschichte](https://www.unicode.org/Public/MAPPINGS/VENDORS/APPLE/CYRILLIC.TXT) |
| UKRAINE | CP1125; [DOSEMU-Referenz](https://github.com/dosemu2/dosemu2/blob/12966165cad849b11c2fed3e99c40baaf3504235/src/plugin/extra_charsets/cp1125.c) |
| CP895 | Kamenický / KEYBCS2, CP437 mit nationalen Zeichen; [DOSEMU-Referenz](https://github.com/dosemu2/dosemu2/blob/12966165cad849b11c2fed3e99c40baaf3504235/src/plugin/extra_charsets/cp895.c) |
| CP896 | Mazovia, CP437 mit polnischen Zeichen; [Kermit-Zeichentabelle](https://www.columbia.edu/kermit/mazovia.html) |
| CWI | CWI-2, CP437 mit acht geänderten Zeichen; [DOSBox-Staging-Definition](https://github.com/dosbox-staging/dosbox-staging/blob/d8669d56a156be670362b4b0247f26bf0d86ed42/resources/mapping/MAIN.TXT) |
| KAMENICT | Historische VC-Variante, nicht identisch mit der regulären CP895-Tabelle; siehe Profile |

Die elf verwendeten Python-Codecs wurden zusätzlich mit den angegebenen
Unicode-/DOSEMU-Referenzen verglichen. Die heruntergeladenen Prüfkopien und
ein SHA-256-Protokoll liegen bei diesem Abgleich unter
`build/codepage-references/`; sie sind keine Build-Eingaben.

## Standard- und Kompatibilitätsprofil

`charsets.xml` enthält Dateinamen, Titel, DOS-Codepage und einen
`conversion`-Auftrag je Einbyte-Tabelle. Es enthält keine 256-Byte-
Ergebnisarrays mehr. Beide XML-Dateien haben eine DTD für XMLmind.

Das voreingestellte Profil **compat** erhält die alte Auslieferung.
Es ergänzt die Unicode-Berechnung um ausdrücklich benannte Regeln:
`replace` für Ersatzzeichen, `omit` für historische Auslassungen und
`undefined` für zwei alte Zuordnungen an eigentlich undefinierten
CP1250-Positionen. Beispielsweise wird im alten KOI8-R-Viewer ein © als
c dargestellt. Solche Entscheidungen stammen aus der ursprünglichen
VC-Tabelle, nicht aus dem Zeichensatzstandard.

Das Profil **standard** verwendet nur die definierten Zeichen:

```sh
python3 tools/assets.py build --profile standard --output build/assets-standard
```

Ein nicht darstellbares Zeichen erhält den TBL-Wert 00; VC zeigt dafür
bei der entsprechenden Anzeige einen Punkt. Auch die drei historischen
Unicode-Sonderfälle entfallen in diesem Profil:

| Tabelle | Historische VC-Ausgabe | Standardausgabe |
|---|---|---|
| CP437 E6 | U+03BC, griechisches Mu | U+00B5, Mikrozeichen |
| CP850 D5 | U+20AC, Eurozeichen | U+0131, punktloses i |
| CP852 AA | U+FFFF, ohne Zuordnung | U+00AC, Negationszeichen |

Die alte KAMENICT-Tabelle lässt AC..FF unverändert durch und hat zwei
weitere abweichende Buchstabenzuordnungen. Dieses Verhalten ist als
historischer Durchreichbereich und benannte Ausnahmen dokumentiert.
Im Standardprofil verwenden CP895 und KAMENICT beide die reguläre
Kamenický-Definition. Mehrere CWI-/Mazovia-/Kamenický-Varianten und
uneindeutige Codepage-Nummern sind historisch belegt; Dateinamen allein
sind kein Beweis für eine bestimmte Belegung.

Im Kompatibilitätsprofil sind alle 15 TBL-Dateien weiter bytegleich mit
der bisherigen Auslieferung. Das Standardprofil unterscheidet sich
bewusst bei 14 Tabellen. Das Profil steht in `manifest.xml`; die alte
Original-Prüfsumme bleibt als Herkunftsangabe erhalten.

Das TBL-Ausgabeformat bleibt: ASCII-Titel bis 60 Zeichen, CRLF, Typbyte
und genau 256 Nutzbytes. Typ 0 enthält 128 Bytes für jede Richtung,
Typ 1 enthält 128 Little-Endian-Unicode-Wörter für Bytes 80..FF.
Die ASCII-Hälfte ergänzt VC selbst.

Zum Benutzen eine Tabelle aus dem passenden CP-Verzeichnis ins VC-
Verzeichnis kopieren und im internen Betrachter mit F8 auswählen.

## Wenn echte Schriftzeichen gemeint sind

Dafür braucht man eine Fontquelle, zum Beispiel eine BDF- oder HEX-
Bitmapschrift. Eine solche Quelle beschreibt tatsächlich die Pixel;
ein Codepage-Generator wählt daraus die 256 passenden Unicode-Glyphen
und erzeugt einen VGA-Font beziehungsweise eine CPI-Datei. Der Treiber
muss diese Glyphen anschließend laden. Eine TBL alleine ändert den
Bildschirmfont nicht.

Ein nachvollziehbarer Kandidat ist [Unscii](https://github.com/viznut/unscii):
Dort stehen Bitmapglyphen als Text im HEX-Format. Im Open386MAX-Arbeitsbaum
wird dieses Verfahren separat für einen optionalen CP437-Font bearbeitet.
VC selbst liefert durch diese TBL-Änderung keinen neuen Font aus.

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
xmllint --noout --valid assets/charsets.xml assets/codepages.xml
xmllint --noout assets/vc-icon.svg
```

Das Repository enthält für seine eigenen Artefakte nur Textquellen:
ASM/C, XML, SVG und die bisherigen Textdateien. Externe DOS-Packer und der
Installer bleiben separate, nachvollziehbare Build-/Download-Abhängigkeiten.
