#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10,<13"]
# ///
"""Audit image edits against an explicit whitelist and independent protection regions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps


def changed_mask(original: Image.Image, edited: Image.Image) -> Image.Image:
    channels = ImageChops.difference(original.convert("RGBA"), edited.convert("RGBA")).split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    return maximum.point(lambda value: 255 if value else 0)


def count(mask: Image.Image) -> int:
    return mask.histogram()[255]


def validate_rectangles(values: object, size: tuple[int, int], label: str) -> list[list[int]]:
    if not isinstance(values, list):
        raise ValueError(f"{label} must be a list of rectangles")
    for box in values:
        if not isinstance(box, list) or len(box) != 4 or any(type(value) is not int for value in box):
            raise ValueError(f"{label}: expected four integer coordinates: {box}")
        left, top, right, bottom = box
        if not (0 <= left < right <= size[0] and 0 <= top < bottom <= size[1]):
            raise ValueError(f"{label}: rectangle outside image or empty: {box}")
    return values


def region_mask(size: tuple[int, int], boxes: list[list[int]]) -> Image.Image:
    result = Image.new("L", size, 0)
    draw = ImageDraw.Draw(result)
    for left, top, right, bottom in boxes:
        draw.rectangle((left, top, right - 1, bottom - 1), fill=255)
    return result


def read_image(path: str) -> Image.Image:
    with Image.open(path) as image:
        image.load()
        return image.copy()


def fingerprint(path: str) -> dict:
    resolved = Path(path).resolve()
    return {"path": str(resolved), "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest()}


def audit(args: argparse.Namespace) -> dict:
    inputs = {Path(value).resolve() for value in (args.original, args.edited, args.regions, args.allowed_mask) if value}
    outputs = [Path(value).resolve() for value in (args.report, args.diff) if value]
    if inputs.intersection(outputs) or len(set(outputs)) != len(outputs):
        raise ValueError("Output paths must be distinct and must not overwrite any input")
    config = json.loads(Path(args.regions).read_text(encoding="utf-8")) if args.regions else {}
    if not isinstance(config, dict):
        raise ValueError("Regions JSON must be an object")
    if args.allowed_mask and "allowed_regions" in config:
        raise ValueError("Use allowed_regions or --allowed-mask, not both")
    original = read_image(args.original)
    edited = read_image(args.edited)
    report = {
        "original": fingerprint(args.original),
        "edited": fingerprint(args.edited),
        "original_size": list(original.size),
        "edited_size": list(edited.size),
        "same_size": original.size == edited.size,
        "translation_quality": "not_assessed",
        "pass": False,
    }
    if original.size != edited.size:
        report["failure"] = "Image dimensions differ; no pixel alignment is assumed."
        return report
    size = original.size
    protected_boxes = validate_rectangles(config.get("protected_regions", []), size, "protected_regions")
    if args.allowed_mask:
        raw_mask = read_image(args.allowed_mask)
        if raw_mask.size != size or raw_mask.mode not in {"1", "L"}:
            raise ValueError("Allowed mask must be same-size grayscale (L or 1)")
        allowed = raw_mask.convert("L").point(lambda value: 255 if value else 0)
    else:
        allowed = region_mask(size, validate_rectangles(config.get("allowed_regions", []), size, "allowed_regions"))
    changed = changed_mask(original, edited)
    outside = ImageChops.multiply(changed, ImageOps.invert(allowed))
    protected = ImageChops.multiply(changed, region_mask(size, protected_boxes))
    protected_results = [
        {"box": box, "changed_pixels": count(changed.crop(tuple(box)))}
        for box in protected_boxes
    ]
    outside_count = count(outside)
    protected_count = count(protected)
    report.update(
        {
            "changed_pixels": count(changed),
            "allowed_pixels": count(allowed),
            "outside_allowed_changed_pixels": outside_count,
            "protected_changed_pixels": protected_count,
            "protected_regions": protected_results,
            "pass": outside_count == 0 and protected_count == 0,
        }
    )
    if args.diff:
        visual = ImageOps.grayscale(edited.convert("RGB")).convert("RGB")
        for mask, color in (
            (changed, (235, 45, 45)),
            (outside, (255, 0, 255)),
            (protected, (255, 165, 0)),
        ):
            visual.paste(color, (0, 0), mask)
        Path(args.diff).parent.mkdir(parents=True, exist_ok=True)
        visual.save(args.diff, format="PNG")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True)
    parser.add_argument("--edited", required=True)
    parser.add_argument("--regions", help="JSON with allowed_regions and/or protected_regions")
    parser.add_argument("--allowed-mask", help="Alternative same-size grayscale edit whitelist")
    parser.add_argument("--report", required=True)
    parser.add_argument("--diff", help="Optional PNG highlighting changed pixels")
    args = parser.parse_args()
    try:
        report = audit(args)
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
