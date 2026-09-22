#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow>=10,<13"]
# ///
"""Inventory EPUB images and surgically pack reviewed replacements."""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import io
import json
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from zipfile import ZIP_STORED, ZipFile
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff", ".avif"}
FORMATS = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
    "GIF": (".gif", "image/gif"),
    "WEBP": (".webp", "image/webp"),
}
XML_EXTS = {".xml", ".opf", ".xhtml", ".html", ".ncx", ".svg"}
ATTR = re.compile(r'''(\b(?:href|src|poster|data)\s*=\s*)(["'])(.*?)(\2)''', re.I | re.S)
CSS_URL = re.compile(r'''(url\(\s*)(["']?)(.*?)(\2)(\s*\))''', re.I)
FONT_OBFUSCATION = {
    "http://www.idpf.org/2008/embedding",
    "http://ns.adobe.com/pdf/enc#RC",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def canonical(name: str) -> str:
    if "\\" in name or name.startswith("/"):
        raise ValueError(f"Unsafe member: {name}")
    value = posixpath.normpath(name)
    if value in {"", ".", ".."} or value.startswith("../"):
        raise ValueError(f"Member escapes EPUB root: {name}")
    return value


def resolve(base_member: str, uri: str) -> str | None:
    parsed = urlsplit(html.unescape(uri))
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path:
        return base_member
    return canonical(posixpath.join(posixpath.dirname(base_member), unquote(parsed.path)))


def read_book(path: Path) -> tuple[dict[str, bytes], dict, bytes, str, ET.Element, list[ET.Element]]:
    with ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP integrity failure: {bad}")
        data: dict[str, bytes] = {}
        infos: dict = {}
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = canonical(info.filename)
            if member in data:
                raise ValueError(f"Duplicate normalized member: {member}")
            if info.flag_bits & 1:
                raise ValueError("Encrypted ZIP entries are unsupported")
            data[member] = archive.read(info)
            infos[member] = info
        if data.get("mimetype") != b"application/epub+zip":
            raise ValueError("Not an EPUB mimetype")
        if "META-INF/encryption.xml" in data:
            encryption = ET.fromstring(data["META-INF/encryption.xml"])
            algorithms = [
                node.get("Algorithm")
                for node in encryption.iter()
                if local_name(node.tag) == "EncryptionMethod"
            ]
            if not algorithms or any(value not in FONT_OBFUSCATION for value in algorithms):
                raise ValueError("DRM/encrypted resources are unsupported")
        container = ET.fromstring(data["META-INF/container.xml"])
        roots = [
            canonical(node.get("full-path", ""))
            for node in container.iter()
            if local_name(node.tag) == "rootfile"
        ]
        if len(roots) != 1:
            raise ValueError("Expected one package rootfile; inspect multi-rendition EPUB manually")
        opf = roots[0]
        package = ET.fromstring(data[opf])
        manifest = [node for node in package.iter() if local_name(node.tag) == "item"]
        return data, infos, archive.comment, opf, package, manifest


def references(member: str, content: bytes) -> list[tuple[str, str | None]]:
    suffix = Path(member).suffix.lower()
    if suffix not in XML_EXTS | {".css"}:
        return []
    text = content.decode("utf-8-sig")
    values = [match.group(3) for match in ATTR.finditer(text)] if suffix in XML_EXTS else []
    values.extend(match.group(3) for match in CSS_URL.finditer(text))
    return [(uri, resolve(member, uri)) for uri in values]


def structural_issues(data: dict[str, bytes], opf: str) -> list[str]:
    issues: list[str] = []
    package = ET.fromstring(data[opf])
    items = {
        node.get("id"): node
        for node in package.iter()
        if local_name(node.tag) == "item"
    }
    anchors: dict[str, set[str]] = {}
    for member, content in data.items():
        if Path(member).suffix.lower() not in XML_EXTS:
            continue
        try:
            root = ET.fromstring(content)
            anchors[member] = {
                value
                for node in root.iter()
                for key, value in node.attrib.items()
                if local_name(key) in {"id", "name"}
            }
        except ET.ParseError:
            anchors[member] = set()
    for member, content in data.items():
        if Path(member).suffix.lower() in XML_EXTS:
            try:
                ET.fromstring(content)
            except ET.ParseError as exc:
                issues.append(f"XML {member}: {exc}")
        for uri, target in references(member, content):
            if target and target not in data:
                issues.append(f"Missing {member} -> {uri}")
            fragment = unquote(urlsplit(html.unescape(uri)).fragment)
            if target in anchors and fragment and not fragment.startswith("epubcfi(") and fragment not in anchors[target]:
                issues.append(f"Missing fragment {member} -> {uri}")
    for node in package.iter():
        if local_name(node.tag) == "itemref" and node.get("idref") not in items:
            issues.append(f"Missing spine id: {node.get('idref')}")
    for item in items.values():
        target = resolve(opf, item.get("href", ""))
        mime = item.get("media-type", "")
        if target not in data or not mime.startswith("image/") or mime == "image/svg+xml":
            continue
        try:
            with Image.open(io.BytesIO(data[target])) as image:
                image.load()
                detected = image.format
            if detected in FORMATS and FORMATS[detected][1] != mime:
                issues.append(f"Image MIME mismatch: {target}: {mime} vs {detected}")
        except (OSError, ValueError) as exc:
            issues.append(f"Image decode {target}: {exc}")
    return sorted(set(issues))


def inspect_book(args: argparse.Namespace) -> None:
    source = Path(args.source).expanduser().resolve()
    work = Path(args.work).expanduser().resolve()
    if (work / "inventory.json").exists() or (work / "decisions.json").exists():
        raise ValueError("Inventory already exists; choose a fresh work directory")
    data, _infos, _comment, opf, package, manifest = read_book(source)
    originals = work / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    by_path: dict[str | None, list[ET.Element]] = {}
    cover_ids = {
        node.get("content")
        for node in package.iter()
        if local_name(node.tag) == "meta" and node.get("name") == "cover"
    }
    for item in manifest:
        by_path.setdefault(resolve(opf, item.get("href", "")), []).append(item)
    used: dict[str, set[str]] = {}
    for member, content in data.items():
        if member == opf:
            continue
        for _uri, target in references(member, content):
            if target:
                used.setdefault(target, set()).add(member)
    images: list[dict] = []
    for member, content in data.items():
        entries = by_path.get(member, [])
        if not (
            Path(member).suffix.lower() in IMAGE_EXTS
            or any(node.get("media-type", "").startswith("image/") for node in entries)
        ):
            continue
        number = len(images) + 1
        destination = originals / f"{number:03d}-{Path(member).name}"
        destination.write_bytes(content)
        record = {
            "member": member,
            "file": str(destination),
            "sha256": sha256(content),
            "bytes": len(content),
            "cover": any(
                "cover-image" in node.get("properties", "").split()
                or node.get("id") in cover_ids
                for node in entries
            ),
            "referenced_by": sorted(used.get(member, set())),
        }
        if Path(member).suffix.lower() == ".svg":
            root = ET.fromstring(content)
            record["svg_text"] = [
                "".join(node.itertext())
                for node in root.iter()
                if local_name(node.tag) == "text"
            ]
        else:
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                record.update(
                    size=list(image.size),
                    format=image.format,
                    frames=getattr(image, "n_frames", 1),
                )
        images.append(record)

    for start in range(0, len(images), 12):
        page = images[start : start + 12]
        sheet = Image.new("RGB", (1200, 330 * ((len(page) + 3) // 4)), "#dedede")
        draw = ImageDraw.Draw(sheet)
        for offset, record in enumerate(page):
            x = (offset % 4) * 300
            y = (offset // 4) * 330
            draw.text((x + 8, y + 6), f"{start + offset + 1:03d} {Path(record['member']).name}", fill="black")
            try:
                with Image.open(record["file"]) as image:
                    preview = image.convert("RGB")
                    preview.thumbnail((284, 294))
                    sheet.paste(preview, (x + (300 - preview.width) // 2, y + 28))
            except OSError:
                draw.text((x + 10, y + 50), "SVG: inspect source/render separately", fill="black")
        sheet.save(work / f"contact-{start // 12 + 1:02d}.png")

    inventory = {
        "source": str(source),
        "sha256": sha256(source.read_bytes()),
        "opf": opf,
        "images": images,
        "structural_issues": structural_issues(data, opf),
    }
    decisions = {
        "source_sha256": inventory["sha256"],
        "instructions": "Review every item. Set decision to translate, keep, or uncertain; record reason, method, and output.",
        "images": [
            {
                "member": record["member"],
                "cover": record["cover"],
                "decision": "unreviewed",
                "reason": "",
                "method": "",
                "output": "",
                "text_review": "pending",
                "visual_review": "pending",
                "pixel_audit": "pending",
                "background_review": "pending" if record["cover"] else "not_applicable",
                "typography_review": "pending" if record["cover"] else "not_applicable",
            }
            for record in images
        ],
    }
    write_json(work / "inventory.json", inventory)
    write_json(work / "decisions.json", decisions)
    print(
        json.dumps(
            {
                "images": len(images),
                "inventory": str(work / "inventory.json"),
                "decisions": str(work / "decisions.json"),
                "issues": inventory["structural_issues"],
            },
            ensure_ascii=False,
        )
    )


def new_uri(member: str, uri: str, renames: dict[str, str]) -> str:
    target = resolve(member, uri)
    if target not in renames:
        return uri
    parsed = urlsplit(html.unescape(uri))
    relative = posixpath.relpath(renames[target], posixpath.dirname(member) or ".")
    return urlunsplit(("", "", quote(relative, safe="/.-_~"), parsed.query, parsed.fragment)).replace("&", "&amp;")


def rewrite_refs(member: str, content: bytes, renames: dict[str, str]) -> bytes:
    suffix = Path(member).suffix.lower()
    if suffix not in XML_EXTS | {".css"}:
        return content
    text = content.decode("utf-8")
    if suffix in XML_EXTS:
        text = ATTR.sub(
            lambda match: match.group(1) + match.group(2) + new_uri(member, match.group(3), renames) + match.group(4),
            text,
        )
    text = CSS_URL.sub(
        lambda match: match.group(1) + match.group(2) + new_uri(member, match.group(3), renames) + match.group(4) + match.group(5),
        text,
    )
    return text.encode("utf-8")


def pack_book(args: argparse.Namespace) -> None:
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    report_path = Path(args.report).expanduser().resolve()
    replacements_path = Path(args.replacements).expanduser().resolve()
    decisions_path = Path(args.decisions).expanduser().resolve()
    if output.exists() or output == source:
        raise ValueError("Output exists or would overwrite source")
    if report_path in {source, output, replacements_path, decisions_path}:
        raise ValueError("Report must not overwrite an input/output")
    data, infos, comment, opf, package, manifest = read_book(source)
    replacements = json.loads(replacements_path.read_text(encoding="utf-8"))
    if not isinstance(replacements, dict):
        raise ValueError("Replacements must be a member-to-file object")
    decisions_payload = json.loads(decisions_path.read_text(encoding="utf-8"))
    if not isinstance(decisions_payload, dict) or not isinstance(decisions_payload.get("images"), list):
        raise ValueError("Decisions must contain an images array")
    if decisions_payload.get("source_sha256") != sha256(source.read_bytes()):
        raise ValueError("Decisions do not match this source EPUB")
    manifest_images = {
        resolve(opf, node.get("href", ""))
        for node in manifest
        if node.get("media-type", "").startswith("image/")
    }
    decisions: dict[str, dict] = {}
    valid_review = {"passed", "checked", "not_applicable"}
    for item in decisions_payload["images"]:
        if not isinstance(item, dict) or not isinstance(item.get("member"), str):
            raise ValueError("Every decision must be an object with a member")
        member = canonical(item["member"])
        if member in decisions:
            raise ValueError(f"Duplicate decision: {member}")
        decision = item.get("decision")
        if decision not in {"translate", "keep", "uncertain"}:
            raise ValueError(f"Image is still unreviewed or has an invalid decision: {member}")
        if not str(item.get("reason", "")).strip():
            raise ValueError(f"Decision reason is required: {member}")
        if decision == "translate":
            if not str(item.get("method", "")).strip():
                raise ValueError(f"Translation method is required: {member}")
            for field in ("text_review", "visual_review", "pixel_audit"):
                if item.get(field) not in valid_review:
                    raise ValueError(f"{field} has not passed: {member}")
            if item.get("cover"):
                for field in ("background_review", "typography_review"):
                    if item.get(field) not in {"passed", "checked"}:
                        raise ValueError(f"Cover {field} has not passed: {member}")
        decisions[member] = item
    if set(decisions) != manifest_images:
        missing = sorted(value for value in manifest_images if value not in decisions)
        extra = sorted(value for value in decisions if value not in manifest_images)
        raise ValueError(f"Decisions do not cover manifest images; missing={missing}, extra={extra}")
    translated = {member for member, item in decisions.items() if item["decision"] == "translate"}
    if set(replacements) != translated:
        raise ValueError("Replacement members must exactly match decisions marked translate")
    for member in translated:
        declared = Path(str(decisions[member].get("output", ""))).expanduser().resolve()
        actual = Path(str(replacements[member])).expanduser().resolve()
        if not decisions[member].get("output") or declared != actual:
            raise ValueError(f"Decision output does not match replacement: {member}")
    before_issues = structural_issues(data, opf)
    changed: dict[str, bytes] = {}
    renames: dict[str, str] = {}
    mimes: dict[str, str] = {}
    for raw_member, filename in replacements.items():
        member = canonical(raw_member)
        if member not in data:
            raise ValueError(f"Replacement target is absent: {member}")
        if not any(
            resolve(opf, node.get("href", "")) == member
            and node.get("media-type", "").startswith("image/")
            for node in manifest
        ):
            raise ValueError(f"Replacement is not a manifest image: {member}")
        replacement = Path(filename).expanduser().resolve()
        content = replacement.read_bytes()
        if content == data[member]:
            continue
        if replacement.suffix.lower() == ".svg":
            ET.fromstring(content)
            extension, mime = ".svg", "image/svg+xml"
            if Path(member).suffix.lower() != ".svg":
                raise ValueError("Raster-to-SVG replacement needs explicit layout review")
        else:
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                if image.format not in FORMATS:
                    raise ValueError(f"Unsupported replacement format: {image.format}")
                extension, mime = FORMATS[image.format]
                size = image.size
            with Image.open(io.BytesIO(data[member])) as original:
                if size != original.size:
                    raise ValueError(f"Replacement dimensions changed: {member}")
                if getattr(original, "n_frames", 1) > 1:
                    raise ValueError("Animated images require a dedicated workflow")
        target = str(Path(member).with_suffix(extension)).replace("\\", "/")
        if target != member and (target in data or target in changed):
            raise ValueError(f"Renamed image collision: {target}")
        changed[target] = content
        renames[member] = target
        mimes[target] = mime

    result: dict[str, bytes] = {}
    for member, content in data.items():
        if member in renames:
            result[renames[member]] = changed[renames[member]]
        else:
            result[member] = rewrite_refs(member, content, renames)

    opf_text = result[opf].decode("utf-8")

    def update_manifest_item(match: re.Match) -> str:
        tag = match.group(0)
        href = re.search(r'''\bhref\s*=\s*(["'])(.*?)\1''', tag)
        if not href:
            return tag
        target = resolve(opf, href.group(2))
        if target not in mimes:
            return tag
        return re.sub(
            r'''(\bmedia-type\s*=\s*)(["'])(.*?)\2''',
            lambda item: item.group(1) + item.group(2) + mimes[target] + item.group(2),
            tag,
        )

    result[opf] = re.sub(r"<(?:\w+:)?item\b[^>]*>", update_manifest_item, opf_text).encode("utf-8")
    checked_text: list[str] = []
    for member, content in data.items():
        if Path(member).suffix.lower() in {".xhtml", ".html"}:
            before = ET.fromstring(content)
            after = ET.fromstring(result[member])
            if list(before.itertext()) != list(after.itertext()):
                raise ValueError(f"Prose changed: {member}")
            checked_text.append(member)
    after_issues = structural_issues(result, opf)
    introduced = sorted(set(after_issues) - set(before_issues))
    if introduced:
        raise ValueError(f"New structural issues: {introduced}")
    before_spine = [node.get("idref") for node in package.iter() if local_name(node.tag) == "itemref"]
    after_spine = [node.get("idref") for node in ET.fromstring(result[opf]).iter() if local_name(node.tag) == "itemref"]
    if before_spine != after_spine:
        raise ValueError("Spine changed")

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        raise ValueError("Partial output already exists")
    try:
        with ZipFile(partial, "x") as archive:
            archive.comment = comment
            archive.writestr("mimetype", b"application/epub+zip", compress_type=ZIP_STORED)
            for member, content in result.items():
                if member == "mimetype":
                    continue
                original = next((old for old, new in renames.items() if new == member), member)
                info = copy.copy(infos[original])
                info.filename = member
                archive.writestr(info, content)
        with ZipFile(partial) as archive:
            if archive.testzip():
                raise ValueError("Final ZIP corruption")
            first = archive.infolist()[0]
            if first.filename != "mimetype" or first.compress_type != ZIP_STORED:
                raise ValueError("Invalid mimetype placement")
            for member, content in result.items():
                if archive.read(member) != content:
                    raise ValueError(f"Output verification failed: {member}")
        with output.open("xb") as handle:
            handle.write(partial.read_bytes())
    finally:
        if partial.exists():
            partial.unlink()

    untouched = [
        member
        for member in data
        if member not in renames and Path(member).suffix.lower() in IMAGE_EXTS
    ]
    report = {
        "source": str(source),
        "output": str(output),
        "source_sha256": sha256(source.read_bytes()),
        "output_sha256": sha256(output.read_bytes()),
        "source_bytes": source.stat().st_size,
        "output_bytes": output.stat().st_size,
        "replacements": renames,
        "modified_image_count": len(renames),
        "unchanged_image_count": len(untouched),
        "unchanged_image_bytes": all(result[name] == data[name] for name in untouched),
        "xhtml_text_checked": len(checked_text),
        "xhtml_text_unchanged": True,
        "existing_structural_issues": before_issues,
        "final_structural_issues": after_issues,
        "new_structural_issues": introduced,
        "mimetype_first_stored": True,
        "zip_verified": True,
        "epubcheck_run": False,
        "decision_counts": {
            value: sum(item["decision"] == value for item in decisions.values())
            for value in ("translate", "keep", "uncertain")
        },
        "complete_image_localization": not any(
            item["decision"] == "uncertain" for item in decisions.values()
        ),
        "uncertain_images": [
            member for member, item in decisions.items() if item["decision"] == "uncertain"
        ],
    }
    write_json(report_path, report)
    print(json.dumps(report, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("source")
    inspect_parser.add_argument("--work", required=True)
    pack_parser = subparsers.add_parser("pack")
    pack_parser.add_argument("source")
    pack_parser.add_argument("--replacements", required=True)
    pack_parser.add_argument("--decisions", required=True)
    pack_parser.add_argument("--output", required=True)
    pack_parser.add_argument("--report", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        (inspect_book if args.command == "inspect" else pack_book)(args)
    except (ValueError, OSError, KeyError, ET.ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
