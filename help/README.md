# VC-Hilfe bearbeiten und bauen

Die bearbeitbaren Quellen sind die XML-Dateien in `src/`: `de.xml`,
`en.xml`, `ru.xml`, `pl.xml` und `sk.xml`. Alle enthalten sowohl die neuen
Kapitel als auch die importierten Referenzseiten. Die JSON- und
Markdown-Zwischenformate werden nicht mehr benötigt. Der
[Referenzabgleich](REFERENCE-AUDIT.md) beschreibt die inhaltliche
Überarbeitung für 4.99.10.

## Mit XMLmind bearbeiten

Zum Beispiel `help/src/de.xml` direkt in XMLmind XML Editor öffnen.
Die relative DOCTYPE-Angabe lädt `help/guide.dtd`; die
`xml-stylesheet`-Anweisung verweist auf `help/guide.css`. DTD und CSS
zusammen mit den XML-Dateien behalten. Die DTD beschreibt die erlaubten
Elemente und Attribute; die CSS-Datei stellt Titel, Absätze und Code im
Editor übersichtlich dar. Die Ansicht ist eine Bearbeitungshilfe;
Zeilenumbrüche und DOS-Zeichen werden beim Kompilieren geprüft.

Neue Texte verwenden `layout="prose"`:

```xml
<topic id="example" layout="prose">
  <title>Ein Beispiel</title>
  <p>Ein Absatz mit <b>fettem</b>, <u>unterstrichenem</u>
     und <code>Code-Text</code>. Version: {{version}}.</p>
  <heading>Befehle</heading>
  <pre>make help</pre>
</topic>
```

`p` wird bei 64 Zeichen umgebrochen. `pre` behält seine Zeilenumbrüche
und darf höchstens 64 Zeichen pro Zeile enthalten. `b` wird fett,
`u` und `code` werden im DOS-Betrachter unterstrichen angezeigt.
Ein Caret `^` in neuen Texten ist normaler Text und wird für den
DOS-Betrachter maskiert. XML-Sonderzeichen wie `&` als `&amp;` schreiben;
XMLmind übernimmt das beim Bearbeiten.

Die historischen Seiten verwenden `layout="ng"` mit einem `line` pro
Originalzeile. Hier bleiben Leerzeichen und Norton-Guides-Steuerfolgen
wie `^b` und `^u` erhalten. DOS-Steuerzeichen, die XML nicht erlaubt,
stehen als `<char code="07"/>` im Text. Diese Seiten können ebenfalls
bearbeitet werden; für eine vollständige Neufassung ist `layout="prose"`
mit Absätzen einfacher. Die ursprünglichen Binärdateien bleiben unter
`original/` zum Vergleichen erhalten.

Jedes Thema braucht eine eindeutige, stabile `id`. In allen fünf Sprachen
müssen dieselben IDs in derselben Reihenfolge vorkommen. Neue Kapitel
also in allen Sprachdateien ergänzen. `project.xml` legt Ausgabedateien,
Sprachen und Zuordnungen der kontextabhängigen F1-Hilfe fest. Ein Kontext
ohne `topic` öffnet das Inhaltsverzeichnis. `historical` kennzeichnet
veraltete 4.05-Referenzseiten im Inhaltsverzeichnis und im Text.

## Erzeugen

```sh
make help                         # fünf HLP-Dateien und VCHELPMAP.INC
make                              # VC mit passender Kontexttabelle
make test                         # Compiler- und Helfertests
make release                      # neue Hilfe ins Release übernehmen
```

Python 3 mit Standardbibliothek reicht für den Hilfe-Compiler.
Die Ausgabe liegt unter `build/help/`. Die Versionsnummer wird aus
`VcVersion` in `src/VCDATA.INC` gelesen. Für eine Hilfe-Vorschau der
geplanten Version 5.0:

```sh
python3 tools/hlp.py build --version 5.0 --output build/help50
```

Das ändert die Versionsnummer des Programms nicht. Vor einem endgültigen
5.0-Release müssen die Versionsnummer und die zugehörigen Texte im
Projekt entsprechend aktualisiert werden. Nach Änderungen an Reihenfolge
oder Kontextzuordnung VC und HLP-Dateien gemeinsam neu bauen und verteilen.
Auch beim DOS-Build zuerst auf dem Host `make help` ausführen.

Die Quellen sind UTF-8. Die Ausgabe verwendet CP437 (Englisch), CP850
(Deutsch), CP866 (Russisch) beziehungsweise CP852 (Polnisch/Slowakisch).
Nicht darstellbare Zeichen, zu große Datensätze und ungültige
Kontextverweise brechen den Build ab. `manifest.xml` verzeichnet Version,
Themenzahl und SHA-256 der erzeugten Dateien.

Optionale vollständige DTD-Prüfung, wenn `xmllint` installiert ist:

```sh
xmllint --noout --valid help/project.xml help/src/*.xml
```

## Binärformat und Originale

VC verwendet eine Variante von Norton Guides, **kein Windows WinHelp**.
`tools/hlp.py` implementiert die tatsächlich vom VC-Betrachter gelesenen
Datensätze einschließlich des sechs Byte breiten Indexverweises und der
XOR-/Leerzeichenkodierung. Die Datensatzgrenze von 2961 Byte folgt aus
dem festen DOS-Hilfepuffer. Ein zu langes Thema muss aufgeteilt werden.
Der Compiler prüft auch die Ausgabe durch erneutes Einlesen.

Die Herkunft der ursprünglichen Hilfen steht in [SOURCES.TXT](SOURCES.TXT).
Die XML-Wurzelelemente enthalten Dateiname und SHA-256 des Originals;
die ursprünglichen Autorenangaben bleiben erhalten. Einen erneuten
Import kann man so erzeugen (Ausgabe unter `help/src/`, damit DTD und CSS
über die relativen Pfade erreichbar sind):

```sh
python3 tools/hlp.py import help/original/VC-GER.HLP help/src/import-de.xml \
  --language de --codepage cp850
```

Formatreferenz: [Norton Guides File Format](https://www.davep.org/norton-guides/file-format/).
Bearbeitungsansicht: [XMLmind CSS Support](https://www.xmlmind.com/xmleditor/_distrib/doc/csssupport/introduction.html).
