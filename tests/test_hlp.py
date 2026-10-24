"""Check the actual VC help layout, historical imports and multilingual build."""
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
import re
import struct
import tempfile
import unittest
from tools import hlp

ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = [("en", "VC.HLP", "cp437"), ("de", "VC-GER.HLP", "cp850"),
             ("ru", "VCR.HLP", "cp866"), ("pl", "VC-PL.HLP", "cp852"),
             ("sk", "VC-SK.HLP", "cp852")]


class HelpCompiler(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)

    def sample(self):
        return [{"id": "first", "title": "First topic", "lines": ["^bTitle^b", "", "Some text."]},
                {"id": "second", "title": "Second topic", "lines": ["^uSecond^u page"]}]

    def test_all_languages_reimport_generated_help_without_binary_inputs(self):
        for code, name, cp in LANGUAGES:
            with self.subTest(code=code):
                source = hlp.read_guide(ROOT / f"help/src/{code}.xml", "test")
                data = hlp.compile_guide(source["topics"], cp, "test", source["credits"])
                decoded = hlp.decompile(data, cp)
                self.assertEqual([(t["title"], t["lines"]) for t in decoded["topics"]],
                                 [(t["title"], t["lines"]) for t in source["topics"]])
                imported = self.out / "import.xml"
                hlp.write_guide(decoded, imported, code, name, hashlib.sha256(data).hexdigest())
                restored = hlp.read_guide(imported, "test")
                self.assertEqual(restored["topics"], decoded["topics"])
                self.assertEqual(restored["credits"], source["credits"])
                self.assertEqual(hlp.compile_guide(restored["topics"], cp, "test", restored["credits"]), data)

    def test_menu_index_and_topic_offsets_match_the_viewer(self):
        topics = self.sample()
        data = hlp.compile_guide(topics, "cp437", "5.0")
        menu, menu_data = hlp.read_entry(data, hlp.HEADER_SIZE)
        self.assertEqual(menu[0], 2)
        root = struct.unpack("<I", hlp.xor(data[0x194:0x198]))[0]
        self.assertEqual(root, struct.unpack_from("<I", menu_data)[0])
        index, payload = hlp.read_entry(data, root)
        self.assertEqual(index[0], 0)
        self.assertEqual(index[2], 2)
        for i, topic in enumerate(topics):
            title, target = hlp.REFERENCE.unpack_from(payload, 6*i)
            self.assertEqual(payload[title:].split(b"\0")[0].decode(), topic["title"])
            header, body = hlp.read_entry(data, target)
            self.assertEqual(header[0], 1)
            self.assertEqual(header[4], i)
            self.assertEqual(header[5], root)
            self.assertEqual(header[2], len(topic["lines"]))
            self.assertEqual(hlp.read_lines(body, header[2]), [s.encode() for s in topic["lines"]])

    def test_compiler_limit_matches_assembly_buffer_layout(self):
        definitions = (ROOT / "src/VCDATA.INC").read_bytes().decode("latin1")
        size = int(re.search(r"LenHelp\s+EQU\s+(\d+)", definitions)[1])
        source = (ROOT / "src/VCHELP.INC").read_text()
        prefix = source.split("HlpHndl\tDW", 1)[1].split("HlpMode", 1)[0]
        before_header = 2 + sum(2 if op == "DW" else 4 for op in re.findall(r"\b(DW|DD)\b", prefix))
        self.assertEqual(before_header, 12)
        self.assertEqual(hlp.MAX_PAYLOAD, size-before_header-hlp.ENTRY.size-1)

    def test_all_current_languages_build_with_identical_topics(self):
        reports = hlp.build(ROOT / "help/project.xml", self.out)
        self.assertEqual(len(reports), 5)
        self.assertEqual({r["topics"] for r in reports},
                         {len(ET.parse(ROOT / "help/src/en.xml").getroot().findall("topic"))})
        for code, name, cp in LANGUAGES:
            data = (self.out / name).read_bytes()
            doc = hlp.decompile(data, cp)
            self.assertIn("VCTOOLS", "\n".join(doc["topics"][5]["lines"]))
            self.assertIn("Retro7Zip", doc["topics"][3]["title"])
            root = struct.unpack("<I", hlp.xor(data[404:408]))[0]
            header, payload = hlp.read_entry(data, root)
            self.assertLess(header[1], 3000-12-26)
            for i in range(header[2]):
                _, offset = hlp.REFERENCE.unpack_from(payload, i*6)
                th, _ = hlp.read_entry(data, offset)
                self.assertLessEqual(th[1], hlp.MAX_PAYLOAD)

    def test_build_rejects_language_order_and_language_mismatches(self):
        tree = ET.parse(ROOT / "help/project.xml")
        project = tree.getroot()
        project.set("definitions", str(ROOT / "src/VCDATA.INC"))
        for lang in project.findall("languages/language"):
            lang.set("source", str(ROOT / "help" / lang.get("source")))
        german = project.find("languages/language[@code='de']")
        altered = self.out / "de.xml"
        german.set("source", str(altered))
        source = ET.parse(ROOT / "help/src/de.xml").getroot()
        # The first two chapters are not both direct dialog targets.
        first, second = source[1], source[2]
        source[1], source[2] = second, first
        ET.ElementTree(source).write(altered, encoding="utf-8")
        path = self.out / "project.xml"
        tree.write(path, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "IDs/order"):
            hlp.build(path, self.out / "bad-order")
        source.set("language", "en")
        ET.ElementTree(source).write(altered, encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "guide language"):
            hlp.build(path, self.out / "bad-language")

    def test_future_release_version_is_not_hardcoded_in_help(self):
        hlp.build(ROOT / "help/project.xml", self.out, "5.0")
        doc = hlp.decompile((self.out / "VC.HLP").read_bytes(), "cp437")
        self.assertIn("Volkov Commander 5.0", " ".join(doc["topics"][0]["lines"]))
        self.assertNotIn("{{version}}", "\n".join(doc["topics"][0]["lines"]))

    def test_current_reference_and_dialog_contexts_replace_old_setup(self):
        hlp.build(ROOT / "help/project.xml", self.out)
        doc = hlp.decompile((self.out / "VC.HLP").read_bytes(), "cp437")
        self.assertFalse(any(t["title"].startswith("[4.05]") for t in doc["topics"]))
        project = ET.parse(ROOT / "help/project.xml").getroot()
        guide = hlp.read_guide(ROOT / "help/src/en.xml", "test")
        pages = {t["id"]: t for t in guide["topics"]}
        self.assertEqual(pages["legacy_40"]["title"], "General options")
        self.assertEqual(pages["legacy_41"]["title"], "Interface options")
        self.assertIn("no handler", " ".join(pages["legacy_38"]["lines"]))
        self.assertIn("without a dialog handler", " ".join(pages["legacy_55"]["lines"]))
        for context, target in [("General_H", "legacy_40"), ("Interface_H", "legacy_41"),
                                ("Descript_H", "legacy_54"), ("CopyOpt_H", "legacy_59")]:
            self.assertEqual(project.find(f"contexts/context[@name='{context}']").get("topic"), target)
        all_text = " ".join(" ".join(t["lines"]) for t in guide["topics"])
        self.assertNotIn("treeinfo.ncd", all_text.lower())

    def test_unicode_encoding_errors_are_reported(self):
        topics = self.sample()
        topics[0]["lines"] = ["Not a DOS character: \U0001f642"]
        with self.assertRaises(UnicodeEncodeError):
            hlp.compile_guide(topics, "cp437", "test")

    def test_rejects_unsafe_empty_and_oversized_records(self):
        for lines in ([], ["bad\0line"], ["bad\nline"], ["x" * hlp.MAX_PAYLOAD]):
            topics = self.sample()
            topics[0]["lines"] = lines
            with self.assertRaises(ValueError):
                hlp.compile_guide(topics, "cp437", "test")
        with self.assertRaises(ValueError):
            hlp.compile_guide(self.sample()*2, "cp437", "test")
        with self.assertRaises(ValueError):
            hlp.compile_guide([], "cp437", "test")

    def test_rejects_oversized_index(self):
        topics = [{"id": f"t{i}", "title": "x" * 60, "lines": ["text"]} for i in range(50)]
        with self.assertRaisesRegex(ValueError, "index needs"):
            hlp.compile_guide(topics, "cp437", "test")

    def test_space_runs_across_the_127_byte_boundary(self):
        for count in (1, 2, 3, 127, 128, 254, 255):
            raw = b"a" + b" " * count + b"z"
            self.assertEqual(hlp.unpack_spaces(hlp.pack_spaces(raw)), raw)
        for raw in (b"\xff", b"\xff\0", b"\xff\x80"):
            with self.assertRaises(ValueError):
                hlp.unpack_spaces(raw)

    def test_corrupt_or_truncated_files_are_rejected(self):
        good = hlp.compile_guide(self.sample(), "cp437", "test")
        for bad in (good[:8], good[:-1], b"BAD!" + good[4:]):
            with self.assertRaises(ValueError):
                hlp.decompile(bad, "cp437")
        broken = bytearray(good)
        broken[404:408] = hlp.xor(struct.pack("<I", len(good)+1))
        with self.assertRaises(ValueError):
            hlp.decompile(broken, "cp437")

    def test_xml_wraps_styles_and_escapes_literal_carets(self):
        path = self.out / "topics.xml"
        path.write_text('<guide language="en" codepage="cp437"><credits/>'
                        '<topic id="intro"><title>Title</title><p><b>' + 'word '*40 +
                        '</b></p><heading>Heading</heading>'
                        '<p>^123E is literal, as is ^b.</p>'
                        '<p>A <u>styled</u> &amp; <code>code</code> example.</p>'
                        '</topic></guide>')
        topics = hlp.read_guide(path, "test")["topics"]
        self.assertIn("^bHeading^b", topics[0]["lines"])
        self.assertIn("^^123E is literal, as is ^^b.", topics[0]["lines"])
        self.assertIn("A ^ustyled^u & ^ucode^u example.", topics[0]["lines"])
        styled = [line for line in topics[0]["lines"] if "word" in line]
        self.assertGreater(len(styled), 1)
        self.assertTrue(all(line.startswith("^b") and line.endswith("^b") for line in styled))
        for content, error in [('<pre>'+'x'*65+'</pre>', 'exceeds'),
                               ('<unknown/>', 'unknown prose'),
                               ('<p><char code="ZZ"/></p>', 'hexadecimal')]:
            path.write_text('<guide language="en" codepage="cp437"><credits/>'
                            '<topic id="intro"><title>Title</title>'+content+'</topic></guide>')
            with self.assertRaisesRegex(ValueError, error):
                hlp.read_guide(path, "test")

    def test_contexts_use_ids_and_fail_on_missing_or_unknown_targets(self):
        definitions = "Default_H EQU 0\nMain_H EQU 1\nNone_H EQU 255\n"
        contexts = {"Default_H": None, "Main_H": "second"}
        result = hlp.context_map(definitions, contexts, self.sample())
        self.assertIn(b"HelpMap DB 0, 2", result)
        contexts["Main_H"] = "missing"
        with self.assertRaisesRegex(ValueError, "unknown topic"):
            hlp.context_map(definitions, contexts, self.sample())
        with self.assertRaisesRegex(ValueError, "missing context"):
            hlp.context_map(definitions, {}, self.sample())
        with self.assertRaisesRegex(ValueError, "unknown help contexts"):
            hlp.context_map(definitions, {"typo_H": None}, self.sample())


if __name__ == "__main__":
    unittest.main()
