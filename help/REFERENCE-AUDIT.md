# Abgleich der Referenz mit VC 4.99.10

Stand: 24. Oktober 2026. Die veröffentlichte Hilfe enthält 73 Themen je
Sprache: elf neue Kapitel und 62 Referenzthemen. Die Herkunft der ursprünglichen
4.05-Hilfe ist in `SOURCES.TXT` und den XML-Metadaten festgehalten.
Die ursprünglichen HLP-Binärdateien sind keine Build-Eingaben mehr.

44 der übernommenen Referenzthemen wurden in allen fünf Sprachen neu
gefasst. Dazu gehören Tastatur, Betrachter, Editor, Fensterarten, Filter,
Laufwerkswahl, Benutzermenüs, Dateizuordnungen, Suche und die Einstellungen.
Die früheren VCSETUP-Seiten beschreiben jetzt die aktuelle Bedienung,
Beschreibungen, Zeichen, Fenster, Farbschema, Kopieroptionen, Länder- und
Codepage-Einstellungen sowie Beenden/Speichern. Die verbliebenen Hinweise
auf `treeinfo.ncd` wurden auf das aktuelle `TREEINFO` korrigiert.

Grundlage des Abgleichs sind die Menütexte und Funktionstabellen in
`src/VCMENU.INC`, die Tastaturbehandlung in `VCFUNC.INC`, `VCVIEW.INC`
und `VCEDIT.INC`, die Suche in `VCFIND.INC`, die Verzeichnisdaten in
`VCTREE.INC` sowie Vorgaben und Dateinamen in `VC.ASM`.

Besonders relevante Korrekturen:

- Einstellungen erfolgen über Options: General, Interface, Characters,
  Panels, Descriptions und Copy and Move. Ein separates VCSETUP gehört
  nicht zum Release.
- Screen saver, Menu file edit, Extension file edit, Viewers und Editors
  haben in der aktuellen Menütabelle keinen Funktionszeiger. Die Hilfe
  kennzeichnet diese Einträge; Menü- und Zuordnungsdateien lassen sich
  direkt als Text bearbeiten.
- Der Betrachter bietet F5 für einen Hex-Offset, F8 für Zeichentabellen
  und Strg-F7 für den vorherigen Suchtreffer. Die Editor-Tasten folgen
  der heutigen Tastaturtabelle.
- Filter bieten vorgegebene Masken aus VCFILTER.EXT und Attributoptionen.
  Lange Namen hängen von der vorhandenen LFN-Schnittstelle ab. Die alte
  pauschale Aussage „alle Namen sind 8.3“ und die Zuordnung über
  Groß-/Kleinschreibung wurden ersetzt.
- F1 kann in Benutzermenüs als Menüeintrag belegt sein; im gelieferten
  Hauptmenü öffnet es Archive. Die Kontextzuordnung nennt die passenden
  aktuellen Einstellungsseiten.

Die weiter gültigen Beschreibungen zu Kopieren, Verschieben, Löschen,
Fensterumschaltung, Speicher, Historie und anderen Grundfunktionen wurden
beibehalten. Deren alte Beispielgrafiken illustrieren die Bedienung;
angezeigte Dateinamen, Größen und Bildschirmrahmen sind Beispiele.

Geprüft werden die XML-Struktur gegen die DTD, alle Sprach-Builds,
Originalimporte, Dateioffsets, feste DOS-Puffergrenzen und Kontextverweise.
Der native DOS-Test prüft die installierte F1-Hilfe zusätzlich in QEMU.
