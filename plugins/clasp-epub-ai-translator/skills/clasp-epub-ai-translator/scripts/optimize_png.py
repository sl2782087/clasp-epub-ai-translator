#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10,<13"]
# ///
"""Optimize a static PNG only when decoded RGBA pixels remain identical."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

from PIL import Image


def optimize(source: Path) -> tuple[bytes, dict]:
    raw = source.read_bytes()
    with Image.open(io.BytesIO(raw)) as opened:
        if opened.format != "PNG":
            raise ValueError("This lossless helper accepts PNG only")
        opened.load()
        image = opened.copy()
        frames = getattr(opened, "n_frames", 1)
    reference = image.convert("RGBA").tobytes()
    choices: list[tuple[str, bytes]] = [("original", raw)]
    report = {
        "source_bytes": len(raw),
        "size": list(image.size),
        "source_mode": image.mode,
        "lossless": True,
    }
    icc = image.info.get("icc_profile")
    unsupported_metadata = any(
        key not in {"transparency", "icc_profile"} for key in image.info
    )
    if (
        frames > 1
        or image.mode not in {"1", "L", "LA", "P", "RGB", "RGBA"}
        or unsupported_metadata
        or (icc and image.mode not in {"RGB", "RGBA", "P"})
    ):
        report["skip_reason"] = "Preserved original animation, high bit depth, or metadata."
    else:

        def candidate(label: str, value: Image.Image, **options: object) -> None:
            buffer = io.BytesIO()
            value.save(
                buffer,
                format="PNG",
                optimize=True,
                compress_level=9,
                **({"icc_profile": icc} if icc else {}),
                **options,
            )
            encoded = buffer.getvalue()
            with Image.open(io.BytesIO(encoded)) as checked:
                checked.load()
                if (
                    checked.size == image.size
                    and checked.convert("RGBA").tobytes() == reference
                    and checked.info.get("icc_profile") == icc
                ):
                    choices.append((label, encoded))

        rgba = Image.frombytes("RGBA", image.size, reference)
        candidate("rgba-optimized", rgba)
        rgb = rgba.convert("RGB")
        red, green, blue = rgb.split()
        neutral = red.tobytes() == green.tobytes() == blue.tobytes()
        alpha = rgba.getchannel("A")
        if alpha.getextrema() == (255, 255):
            candidate("rgb-optimized", rgb)
            if neutral and not icc:
                candidate("grayscale-optimized", Image.frombytes("L", image.size, red.tobytes()))
            colors = rgb.getcolors(257)
            if colors is not None and len(colors) <= 256:
                palette = rgb.convert(
                    "P",
                    palette=Image.Palette.ADAPTIVE,
                    colors=max(2, len(colors)),
                    dither=Image.Dither.NONE,
                )
                bits = next(value for value in (1, 2, 4, 8) if 2**value >= len(colors))
                candidate("exact-palette-optimized", palette, bits=bits)
        elif neutral and not icc:
            candidate("grayscale-alpha-optimized", Image.merge("LA", (red, alpha)))
    method, result = min(choices, key=lambda value: len(value[1]))
    report.update(
        method=method,
        output_bytes=len(result),
        saved_bytes=len(raw) - len(result),
        decoded_rgba_identical=True,
        candidates=[{"method": name, "bytes": len(data)} for name, data in choices],
    )
    return result, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    if len({source, output, report_path}) != 3 or output.exists() or report_path.exists():
        parser.error("Use distinct paths and new output/report files")
    if output.suffix.lower() != ".png":
        parser.error("Output must use the .png extension")
    try:
        content, report = optimize(source)
        output.parent.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as handle:
            handle.write(content)
        with Image.open(output) as saved, Image.open(source) as original:
            if saved.convert("RGBA").tobytes() != original.convert("RGBA").tobytes():
                raise ValueError("Optimized PNG pixels changed")
        report.update(source=str(source), output=str(output))
        with report_path.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        print(json.dumps(report, ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
