from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import audit_regions  # noqa: E402
import epub_images  # noqa: E402
import epub_translate  # noqa: E402
import optimize_png  # noqa: E402


def image_bytes(format_name: str, color: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (160, 100), color).save(buffer, format_name)
    return buffer.getvalue()


def write_book(path: Path, *, embedded_glossary: bool = False) -> tuple[bytes, bytes]:
    cover = image_bytes("PNG", "navy")
    diagram = image_bytes("JPEG", "white")
    members = {
        "META-INF/container.xml": b'''<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''',
        "EPUB/package.opf": b'''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0"><metadata><dc:title>Test Book</dc:title><dc:creator>Test Author</dc:creator><dc:language>ja</dc:language><meta name="cover" content="cover"/></metadata><manifest><item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml"/><item id="cover" href="cover.png" media-type="image/png" properties="cover-image"/><item id="diagram" href="map.jpg" media-type="image/jpeg"/></manifest><spine><itemref idref="chapter"/></spine></package>''',
        "EPUB/chapter.xhtml": b'''<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml"><body><p>Nearby translated prose mentions Makabe and a timetable.</p><figure><img src="map.jpg"/></figure><img src="cover.png"/></body></html>''',
        "EPUB/cover.png": cover,
        "EPUB/map.jpg": diagram,
    }
    if embedded_glossary:
        members["EPUB/package.opf"] = members["EPUB/package.opf"].replace(
            b"</manifest>",
            b'<item id="bbm-glossary" href="bbm_glossary.txt" media-type="text/plain"/></manifest>',
        )
        members["EPUB/bbm_glossary.txt"] = "真壁 -> 真壁 # 人物名\n".encode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for member, content in members.items():
            archive.writestr(member, content)
    return cover, diagram


class ImageWorkflowTests(unittest.TestCase):
    def test_review_mode_does_not_require_experimental_image_models(self) -> None:
        form = {key: str(value) for key, value in epub_translate.DEFAULT_SETTINGS.items()}
        form.update(
            engine="codex",
            image_translation="review",
            image_vision_model="",
            image_edit_model="",
        )
        values = epub_translate.validate_settings(form)
        self.assertEqual(values["image_translation"], "review")

        form["image_translation"] = "auto"
        with self.assertRaisesRegex(ValueError, "必须选择"):
            epub_translate.validate_settings(form)

        page = epub_translate.configuration_page(
            {**epub_translate.DEFAULT_SETTINGS, "image_translation": "review"},
            "test-token",
        )
        self.assertIn("高保真逐图审阅", page)
        self.assertIn("id=\"image_experimental\"", page)
        self.assertIn("updateImageMode()", page)

    def test_inventory_includes_cover_and_decision_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source)
            work = root / "review"
            epub_images.inspect_book(argparse.Namespace(source=str(source), work=str(work)))

            inventory = json.loads((work / "inventory.json").read_text(encoding="utf-8"))
            decisions = json.loads((work / "decisions.json").read_text(encoding="utf-8"))
            self.assertEqual(len(inventory["images"]), 2)
            self.assertTrue(any(item["cover"] for item in inventory["images"]))
            self.assertEqual(
                {item["decision"] for item in decisions["images"]}, {"unreviewed"}
            )
            self.assertTrue((work / "contact-01.png").is_file())
            context = json.loads((work / "image-context.json").read_text(encoding="utf-8"))
            map_context = next(item for item in context["images"] if item["member"] == "EPUB/map.jpg")
            self.assertIn("Nearby translated prose", " ".join(map_context["nearby_text"]))
            self.assertEqual(context["book"]["title"], "Test Book")

    def test_pack_renames_format_and_preserves_prose_and_untouched_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            cover, _diagram = write_book(source)
            replacement = root / "map.png"
            replacement.write_bytes(image_bytes("PNG", "beige"))
            review = root / "review"
            epub_images.inspect_book(argparse.Namespace(source=str(source), work=str(review)))
            decisions_path = review / "decisions.json"
            decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            for item in decisions["images"]:
                if item["member"] == "EPUB/map.jpg":
                    item.update(
                        decision="translate",
                        reason="Japanese labels require localization",
                        method="flat-background local erase and typesetting",
                        output=str(replacement),
                        recognized_text="時刻表",
                        translation_text="时刻表",
                        matched_terms=[],
                        terminology_review="not_applicable",
                        text_review="passed",
                        visual_review="passed",
                        pixel_audit="passed",
                    )
                else:
                    item.update(decision="keep", reason="Cover contains no source-language text")
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            replacements = root / "replacements.json"
            replacements.write_text(
                json.dumps({"EPUB/map.jpg": str(replacement)}), encoding="utf-8"
            )
            output = root / "localized.epub"
            report = root / "report.json"
            epub_images.pack_book(
                argparse.Namespace(
                    source=str(source),
                    output=str(output),
                    report=str(report),
                    replacements=str(replacements),
                    decisions=str(decisions_path),
                    context=str(review / "image-context.json"),
                )
            )

            with zipfile.ZipFile(output) as archive:
                self.assertIn("EPUB/map.png", archive.namelist())
                self.assertNotIn("EPUB/map.jpg", archive.namelist())
                self.assertEqual(archive.read("EPUB/cover.png"), cover)
                package = archive.read("EPUB/package.opf")
                chapter = archive.read("EPUB/chapter.xhtml")
                self.assertIn(b'href="map.png"', package)
                self.assertIn(b'media-type="image/png"', package)
                self.assertIn(b'src="map.png"', chapter)
                self.assertIn(b"Nearby translated prose mentions Makabe", chapter)
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(payload["xhtml_text_unchanged"])
            self.assertTrue(payload["unchanged_image_bytes"])
            self.assertTrue(payload["complete_image_localization"])

    def test_pack_rejects_unreviewed_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source)
            review = root / "review"
            epub_images.inspect_book(argparse.Namespace(source=str(source), work=str(review)))
            replacements = root / "replacements.json"
            replacements.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unreviewed"):
                epub_images.pack_book(
                    argparse.Namespace(
                        source=str(source),
                        output=str(root / "output.epub"),
                        report=str(root / "report.json"),
                        replacements=str(replacements),
                        decisions=str(review / "decisions.json"),
                        context=str(review / "image-context.json"),
                    )
                )

    def test_context_merges_glossaries_and_reports_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source, embedded_glossary=True)
            glossary = root / "terms.txt"
            glossary.write_text("真壁 -> 真壁先生 # preferred\n時刻表 -> 时刻表\n", encoding="utf-8")
            handoff = root / "book_handoff.md"
            handoff.write_text(
                "## Summary\n\nKeep the mystery clues exact.\n\n"
                "## Style\n\nFaithful literary Chinese.\n\n"
                "## Established renderings\n\n真壁 -> 真壁君\n館長 -> 馆长\n",
                encoding="utf-8",
            )
            review = root / "review"
            epub_images.inspect_book(
                argparse.Namespace(
                    source=str(source),
                    work=str(review),
                    glossary=str(glossary),
                    handoff=str(handoff),
                )
            )
            context = json.loads((review / "image-context.json").read_text(encoding="utf-8"))
            terms = {item["source"]: item for item in context["terminology"]}
            self.assertEqual(terms["真壁"]["translation"], "真壁先生")
            self.assertEqual(terms["真壁"]["origin"], "explicit-glossary")
            self.assertEqual(terms["館長"]["translation"], "馆长")
            self.assertEqual(len(context["terminology_conflicts"]), 2)
            self.assertEqual(context["handoff"]["summary"], "Keep the mystery clues exact.")

    def test_pack_enforces_matched_terminology(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source)
            glossary = root / "terms.txt"
            glossary.write_text("真壁 -> 真壁先生 # character\n", encoding="utf-8")
            review = root / "review"
            epub_images.inspect_book(
                argparse.Namespace(
                    source=str(source), work=str(review), glossary=str(glossary), handoff=None
                )
            )
            replacement = root / "map.png"
            replacement.write_bytes(image_bytes("PNG", "beige"))
            decisions_path = review / "decisions.json"
            decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
            for item in decisions["images"]:
                if item["member"] == "EPUB/map.jpg":
                    item.update(
                        decision="translate",
                        reason="labels",
                        method="local typesetting",
                        output=str(replacement),
                        recognized_text="真壁の時刻表",
                        translation_text="真壁的时刻表",
                        matched_terms=[],
                        terminology_review="passed",
                        text_review="passed",
                        visual_review="passed",
                        pixel_audit="passed",
                    )
                else:
                    item.update(decision="keep", reason="no text")
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            replacements = root / "replacements.json"
            replacements.write_text(json.dumps({"EPUB/map.jpg": str(replacement)}), encoding="utf-8")
            args = argparse.Namespace(
                source=str(source),
                output=str(root / "output.epub"),
                report=str(root / "report.json"),
                replacements=str(replacements),
                decisions=str(decisions_path),
                context=str(review / "image-context.json"),
            )
            with self.assertRaisesRegex(ValueError, "Matched terminology is incomplete"):
                epub_images.pack_book(args)
            translated = next(
                item for item in decisions["images"] if item["member"] == "EPUB/map.jpg"
            )
            translated["matched_terms"] = ["真壁"]
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Required terminology rendering"):
                epub_images.pack_book(args)
            translated["translation_text"] = "真壁先生的时刻表"
            decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
            epub_images.pack_book(args)
            self.assertTrue(Path(args.output).is_file())

    def test_pack_rejects_changed_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source)
            review = root / "review"
            epub_images.inspect_book(argparse.Namespace(source=str(source), work=str(review)))
            context_path = review / "image-context.json"
            context = json.loads(context_path.read_text(encoding="utf-8"))
            context["warnings"].append("changed")
            context_path.write_text(json.dumps(context), encoding="utf-8")
            replacements = root / "replacements.json"
            replacements.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum"):
                epub_images.pack_book(
                    argparse.Namespace(
                        source=str(source),
                        output=str(root / "output.epub"),
                        report=str(root / "report.json"),
                        replacements=str(replacements),
                        decisions=str(review / "decisions.json"),
                        context=str(context_path),
                    )
                )

    def test_pixel_audit_uses_independent_allowed_and_protected_regions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            original = root / "original.png"
            edited = root / "edited.png"
            Image.new("RGB", (20, 20), "white").save(original)
            changed = Image.open(original).copy()
            ImageDraw.Draw(changed).rectangle((2, 2, 4, 4), fill="black")
            changed.save(edited)
            regions = root / "regions.json"
            regions.write_text(
                json.dumps(
                    {
                        "allowed_regions": [[2, 2, 5, 5]],
                        "protected_regions": [[10, 10, 15, 15]],
                    }
                ),
                encoding="utf-8",
            )
            report = audit_regions.audit(
                argparse.Namespace(
                    original=str(original),
                    edited=str(edited),
                    regions=str(regions),
                    allowed_mask=None,
                    report=str(root / "audit.json"),
                    diff=None,
                )
            )
            self.assertTrue(report["pass"])
            self.assertEqual(report["outside_allowed_changed_pixels"], 0)

    def test_png_optimization_preserves_decoded_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name) / "master.png"
            Image.new("RGBA", (64, 64), (240, 240, 240, 255)).save(source)
            encoded, report = optimize_png.optimize(source)
            with Image.open(io.BytesIO(encoded)) as result, Image.open(source) as original:
                self.assertEqual(result.convert("RGBA").tobytes(), original.convert("RGBA").tobytes())
            self.assertTrue(report["decoded_rgba_identical"])

    def test_wrapper_prepares_review_and_never_calls_image_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "book.epub"
            write_book(source)
            work = root / "work"
            work.mkdir()
            report = epub_translate.prepare_image_review(source, work, resume=False)
            self.assertEqual(report["status"], "review_required")
            self.assertEqual(report["image_count"], 2)
            self.assertTrue(Path(report["decisions"]).is_file())
            self.assertTrue(Path(report["context"]).is_file())


if __name__ == "__main__":
    unittest.main()
