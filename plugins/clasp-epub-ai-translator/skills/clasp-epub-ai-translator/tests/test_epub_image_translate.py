from __future__ import annotations

import base64
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image, ImageFont


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import epub_image_translate as image_translate  # noqa: E402
import epub_translate  # noqa: E402


REGION = {
    "source": "東京",
    "translation": "东京",
    "bbox": [0.3, 0.3, 0.7, 0.7],
    "writing_mode": "horizontal",
}


def png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


class ImageTranslationTests(unittest.TestCase):
    def test_inpaint_composites_only_mask(self) -> None:
        source = Image.new("RGBA", (100, 100), (40, 80, 120, 255))
        mask = image_translate.make_mask(source.size, [REGION])
        generated = png_bytes(Image.new("RGBA", (125, 125), (220, 30, 40, 255)))
        response = {"data": [{"b64_json": base64.b64encode(generated).decode("ascii")}]}
        with mock.patch.object(image_translate, "_request", return_value=response):
            result = image_translate.inpaint(source, mask, "https://example.test/v1", "test-key", "image-model", "low")
        self.assertEqual(result.getpixel((0, 0)), source.getpixel((0, 0)))
        self.assertEqual(result.getpixel((99, 99)), source.getpixel((99, 99)))
        self.assertNotEqual(result.getpixel((50, 50)), source.getpixel((50, 50)))

    def test_render_is_clipped_to_region(self) -> None:
        source = Image.new("RGBA", (300, 200), (245, 245, 240, 255))
        with mock.patch.object(image_translate, "_font", side_effect=lambda _size: ImageFont.load_default()):
            result = image_translate.render_translations(source, [REGION])
        self.assertEqual(result.getpixel((0, 0)), source.getpixel((0, 0)))
        self.assertEqual(result.getpixel((299, 199)), source.getpixel((299, 199)))
        self.assertNotEqual(result.crop((90, 60, 210, 140)).tobytes(), source.crop((90, 60, 210, 140)).tobytes())

    def test_epub_repack_updates_mime_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            source = root / "source.epub"
            destination = root / "translated.epub"
            work = root / "work"
            cover = png_bytes(Image.new("RGB", (200, 300), "navy"))
            map_buffer = io.BytesIO()
            Image.new("RGB", (240, 180), "white").save(map_buffer, "JPEG", quality=95)
            members = {
                "mimetype": b"application/epub+zip",
                "META-INF/container.xml": b'''<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>''',
                "EPUB/package.opf": b'''<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0"><metadata><meta name="cover" content="cover"/></metadata><manifest><item id="cover" href="cover.png" media-type="image/png" properties="cover-image"/><item id="map" href="map.jpg" media-type="image/jpeg"/></manifest><spine/></package>''',
                "EPUB/cover.png": cover,
                "EPUB/map.jpg": map_buffer.getvalue(),
            }
            with zipfile.ZipFile(source, "w") as zf:
                zf.writestr("mimetype", members.pop("mimetype"), compress_type=zipfile.ZIP_STORED)
                for name, data in members.items():
                    zf.writestr(name, data)

            def fake_inpaint(image, mask, *_args, **_kwargs):
                return image.copy()

            with mock.patch.object(image_translate, "analyze_image", return_value=[REGION]), mock.patch.object(
                image_translate, "inpaint", side_effect=fake_inpaint
            ), mock.patch.object(image_translate, "_font", side_effect=lambda _size: ImageFont.load_default()):
                report = image_translate.translate_epub_images(
                    source, destination, work, mode="auto", api_base="https://example.test/v1", api_key="test-key",
                    vision_model="vision", edit_model="image", quality="low", limit=2,
                    include_cover=False, language="zh-hans",
                )
            self.assertEqual(len(report["translated"]), 1)
            self.assertTrue(any(item["reason"] == "cover" for item in report["skipped"]))
            with zipfile.ZipFile(destination) as zf:
                self.assertEqual(zf.read("EPUB/map.jpg")[:8], b"\x89PNG\r\n\x1a\n")
                self.assertIn(b'media-type="image/png"', zf.read("EPUB/package.opf"))
            self.assertTrue(epub_translate.verify_epub(destination)["ok"])


if __name__ == "__main__":
    unittest.main()
