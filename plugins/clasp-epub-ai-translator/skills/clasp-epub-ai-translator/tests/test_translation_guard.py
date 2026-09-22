from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import epub_translate  # noqa: E402
from translation_guard import verify_translation_content  # noqa: E402

CONTAMINATED = (
    "译文开头。}]} Wait source last has opening Japanese quote and no close? "
    "It ends `"
)


def write_epub(
    path: Path,
    chapter_body: str,
    *,
    non_spine_body: str = "附录",
    include_image: bool = True,
) -> Path:
    package = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Test</dc:title></metadata>
  <manifest>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/>
    <item id="appendix" href="appendix.xhtml" media-type="application/xhtml+xml"/>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="image" href="image.png" media-type="image/png"/>
  </manifest>
  <spine><itemref idref="chapter"/></spine>
</package>""".encode()
    chapter = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Chapter</title></head>
<body>{chapter_body}</body></html>""".encode()
    appendix = f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><p>{non_spine_body}</p></body></html>""".encode()
    nav = b"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><nav><a href="chapter.xhtml#anchor">Chapter</a></nav></body></html>"""
    container = b"""<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
<rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("EPUB/package.opf", package)
        zf.writestr("EPUB/chapter.xhtml", chapter)
        zf.writestr("EPUB/appendix.xhtml", appendix)
        zf.writestr("EPUB/nav.xhtml", nav)
        if include_image:
            zf.writestr("EPUB/image.png", b"\x89PNG\r\n\x1a\nfixture")
    return path


class TranslationGuardTests(unittest.TestCase):
    def test_known_residue_fails_with_member_and_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = write_epub(
                Path(temp_name) / "book.epub",
                f'<p><span id="kobo.1188.1">{CONTAMINATED}</span></p>',
            )

            report = verify_translation_content(path)

            self.assertFalse(report["ok"])
            finding = report["findings"][0]
            self.assertEqual(finding["member"], "EPUB/chapter.xhtml")
            self.assertEqual(finding["anchor"], "kobo.1188.1")
            self.assertIn(
                "model-source-self-check", {item["rule"] for item in report["findings"]}
            )

    def test_legal_english_json_and_cross_paragraph_quotes_pass(self) -> None:
        body = """
<p id="a">“这是跨段引语的第一段。</p><p id="b">这是第二段。”</p>
<p>Wait, source the parts from London before dawn.</p>
<pre>```json {"schema": 1, "translation": "legal example"} ```</pre>"""
        with tempfile.TemporaryDirectory() as temp_name:
            report = verify_translation_content(
                write_epub(Path(temp_name) / "book.epub", body)
            )
        self.assertTrue(report["ok"])
        self.assertEqual(report["findings"], [])

    def test_medium_signal_warns_but_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            report = verify_translation_content(
                write_epub(
                    Path(temp_name) / "book.epub", '<p id="a">Analysis: A Novel</p>'
                )
            )
        self.assertTrue(report["ok"])
        self.assertEqual(report["warnings"][0]["rule"], "process-label")

    def test_code_fence_with_process_language_is_rejected(self) -> None:
        body = """<pre id="code">```json {"id": 7, "translation": "译文"} ```
Analysis: I need to check the translation field.</pre>"""
        with tempfile.TemporaryDirectory() as temp_name:
            report = verify_translation_content(
                write_epub(Path(temp_name) / "book.epub", body)
            )
        self.assertFalse(report["ok"])
        self.assertIn(
            "code-fence-with-analysis-schema",
            {item["rule"] for item in report["findings"]},
        )

    def test_non_spine_and_script_style_text_are_ignored(self) -> None:
        body = f"""<script>{CONTAMINATED}</script><style>.x{{content:"{CONTAMINATED}"}}</style><p>正常译文</p>"""
        with tempfile.TemporaryDirectory() as temp_name:
            report = verify_translation_content(
                write_epub(
                    Path(temp_name) / "book.epub",
                    body,
                    non_spine_body=CONTAMINATED,
                )
            )
        self.assertTrue(report["ok"])
        self.assertEqual(report["findings"], [])

    def test_failed_final_gate_does_not_publish_final_epub(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = write_epub(
                root / "source.epub",
                f'<p id="kobo.1188.1">{CONTAMINATED}</p>',
            )
            final = root / "translated.epub"
            work = root / ".work"
            work.mkdir()

            with self.assertRaisesRegex(ValueError, "EPUB/chapter.xhtml#kobo.1188.1"):
                epub_translate.finalize_epub_delivery(source, final, work, "preserve")

            self.assertFalse(final.exists())
            report = json.loads((work / "content-validation-report.json").read_text())
            self.assertEqual(report["content_validation"]["status"], "failed")
            self.assertTrue(list(work.glob(".delivery-*.epub")))

    def test_content_gate_still_runs_when_structure_validation_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = write_epub(
                root / "source.epub",
                f'<p id="kobo.1188.1">{CONTAMINATED}</p>',
                include_image=False,
            )
            final = root / "translated.epub"
            work = root / ".work"
            work.mkdir()

            with self.assertRaisesRegex(ValueError, "missing manifest resources"):
                epub_translate.finalize_epub_delivery(source, final, work, "preserve")

            report = json.loads((work / "content-validation-report.json").read_text())
            self.assertFalse(report["structure_validation"]["ok"])
            self.assertEqual(report["content_validation"]["status"], "failed")
            self.assertEqual(
                report["content_validation"]["findings"][0]["anchor"],
                "kobo.1188.1",
            )

    def test_successful_atomic_delivery_preserves_resources_and_markup(self) -> None:
        body = """<p id="anchor"><ruby><rb>汉字</rb><rt>かんじ</rt></ruby>
<a href="chapter.xhtml#anchor">内部链接</a></p>"""
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = write_epub(root / "source.epub", body)
            final = root / "translated.epub"
            work = root / ".work"
            work.mkdir()

            _, structure, content, _ = epub_translate.finalize_epub_delivery(
                source, final, work, "preserve"
            )

            self.assertTrue(structure["ok"])
            self.assertTrue(content["ok"])
            self.assertTrue(final.is_file())
            with zipfile.ZipFile(final) as zf:
                first = zf.infolist()[0]
                self.assertEqual(first.filename, "mimetype")
                self.assertEqual(first.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(zf.read("EPUB/image.png"), b"\x89PNG\r\n\x1a\nfixture")
                chapter = zf.read("EPUB/chapter.xhtml")
                self.assertIn(b"<ruby>", chapter)
                self.assertIn(b'href="chapter.xhtml#anchor"', chapter)
                self.assertIn("EPUB/nav.xhtml", zf.namelist())


if __name__ == "__main__":
    unittest.main()
