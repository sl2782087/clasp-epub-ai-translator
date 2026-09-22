"""Final EPUB content gate for model-process text in visible spine content.

This module intentionally uses only the Python standard library so the skill
can run before or independently of the translator package installation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import posixpath
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

PROMPT_POLICY_VERSION = "2026-09-22.1"
CONTAMINATION_DETECTOR_VERSION = "2026-09-22.1"
RETRANSLATION_POLICY_VERSION = "2026-09-22.1"


@dataclass(frozen=True)
class ContentIssue:
    confidence: str
    rule: str
    excerpt: str
    start: int
    end: int


_META_PATTERNS = (
    re.compile(
        r"\bwait\s*[,.:;!?-]*\s+(?:the\s+)?source\s+"
        r"(?:last|text|paragraph|sentence)\b",
        re.I,
    ),
    re.compile(
        r"\bsource\s+(?:last|text|paragraph|sentence)\s+"
        r"(?:has|have|contains?|ends?|starts?|opens?|closes?)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:opening|closing|unclosed|unterminated)\s+"
        r"(?:Japanese\s+)?quot(?:e|ation)(?:\s+mark)?\b"
        r"|\bno\s+(?:close|closing)\s*(?:quote|mark)?\s*\?",
        re.I,
    ),
)
_MODEL_WORK = re.compile(
    r"\bI\s+(?:need|must|should|will|have)\s+to\s+"
    r"(?:translate|fix|ensure|check|preserve|return|remove|add)\b",
    re.I,
)
_WORK_OBJECT = re.compile(
    r"\b(?:source|output|translation|translated\s+content|translation\s+field|"
    r"JSON|schema|punctuation|paragraph|Japanese\s+quote|target\s+language)\b",
    re.I,
)
_JSON_TAIL = re.compile(r"(?:}\s*]\s*}|]\s*}|}\s*})")
_FENCE = re.compile(r"```(?:json|javascript|python|xml)?", re.I)
_PROCESS_LABEL = re.compile(
    r"(?im)^\s*(?:analysis|reasoning|self[- ]?check|translation\s+note|"
    r"translator['’]s\s+note)\s*:"
)
_PROCESS_WORD = re.compile(
    r"\b(?:analysis|reasoning|self[- ]?check|translation\s+note)\b",
    re.I,
)
_STRUCTURED_FRAGMENT = re.compile(
    r"[\[{]\s*[\"']?(?:id|translated|translation|paragraphs?)[\"']?\s*:",
    re.I,
)
_AI_DISCLAIMER = re.compile(r"\bas an AI(?: language model)?\b", re.I)

_SKIP_ELEMENTS = {"head", "script", "style", "noscript", "template"}
_BLOCK_ELEMENTS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "dd",
    "div",
    "dt",
    "figcaption",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "li",
    "main",
    "p",
    "pre",
    "section",
    "td",
    "th",
}


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _excerpt(text: str, start: int, end: int, radius: int = 90) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    value = " ".join(text[left:right].split())
    if left:
        value = "…" + value
    if right < len(text):
        value += "…"
    return value[:240]


def detect_translation_contamination(text: str) -> list[ContentIssue]:
    """Return conservative high-confidence failures and medium warnings."""

    text = str(text or "")
    issues: list[ContentIssue] = []
    seen: set[tuple[str, int, int]] = set()

    def add(confidence: str, rule: str, match) -> None:
        start, end = match.span()
        key = (rule, start, end)
        if key in seen:
            return
        seen.add(key)
        issues.append(
            ContentIssue(confidence, rule, _excerpt(text, start, end), start, end)
        )

    for pattern in _META_PATTERNS:
        for match in pattern.finditer(text):
            add("high", "model-source-self-check", match)

    for match in _MODEL_WORK.finditer(text):
        left = max(
            text.rfind("\n", 0, match.start()), text.rfind("。", 0, match.start())
        )
        ends = [
            pos
            for pos in (
                text.find("\n", match.end()),
                text.find("。", match.end()),
                text.find(".", match.end()),
            )
            if pos >= 0
        ]
        right = min(ends) if ends else min(len(text), match.end() + 220)
        if _WORK_OBJECT.search(text[max(0, left) : right]):
            add("high", "model-work-statement", match)

    for match in _JSON_TAIL.finditer(text):
        nearby = text[match.end() : match.end() + 280]
        if any(
            pattern.search(nearby) for pattern in _META_PATTERNS
        ) or _MODEL_WORK.search(nearby):
            add("high", "json-tail-followed-by-self-check", match)

    for match in _FENCE.finditer(text):
        nearby = text[max(0, match.start() - 80) : match.end() + 320]
        if _PROCESS_WORD.search(nearby) and (
            _STRUCTURED_FRAGMENT.search(nearby) or _PROCESS_LABEL.search(nearby)
        ):
            add("high", "code-fence-with-analysis-schema", match)

    for match in _AI_DISCLAIMER.finditer(text):
        if _WORK_OBJECT.search(text[match.start() : match.end() + 220]):
            add("high", "ai-process-disclaimer", match)

    for match in _PROCESS_LABEL.finditer(text):
        if not any(issue.start <= match.start() <= issue.end for issue in issues):
            add("medium", "process-label", match)

    for match in _STRUCTURED_FRAGMENT.finditer(text):
        nearby = text[max(0, match.start() - 120) : match.end() + 240]
        if _PROCESS_WORD.search(nearby) and not any(
            issue.start <= match.start() <= issue.end for issue in issues
        ):
            add("medium", "schema-like-fragment", match)

    return sorted(issues, key=lambda issue: (issue.start, issue.rule))


def _resolve_member(base: PurePosixPath, href: str) -> str:
    clean = urllib.parse.unquote(href.split("#", 1)[0].split("?", 1)[0])
    return posixpath.normpath(posixpath.join(str(base), clean)) if clean else ""


def _package_path(zf: zipfile.ZipFile) -> str:
    root = ET.fromstring(zf.read("META-INF/container.xml"))
    for node in root.iter():
        if _local_name(node.tag) == "rootfile" and node.get("full-path"):
            return node.get("full-path") or ""
    raise ValueError("container.xml does not name an OPF package")


def _visible_text(element: ET.Element) -> str:
    parts: list[str] = []

    def visit(node: ET.Element) -> None:
        if _local_name(node.tag) in _SKIP_ELEMENTS:
            return
        if node.text:
            parts.append(node.text)
        for child in node:
            visit(child)
            if child.tail:
                parts.append(child.tail)

    visit(element)
    return " ".join("".join(parts).split())


def _anchor(element: ET.Element) -> str:
    if element.get("id"):
        return element.get("id") or "(no-id)"
    for descendant in element.iter():
        if descendant.get("id"):
            return descendant.get("id") or "(no-id)"
    return "(no-id)"


def _candidate_elements(body: ET.Element) -> list[ET.Element]:
    candidates: list[ET.Element] = []

    def visit(node: ET.Element) -> None:
        if _local_name(node.tag) in _SKIP_ELEMENTS:
            return
        for child in node:
            visit(child)
        if node.get("id") or _local_name(node.tag) in _BLOCK_ELEMENTS:
            candidates.append(node)

    visit(body)
    if body not in candidates:
        candidates.append(body)
    return candidates


def verify_translation_content(path: Path) -> dict:
    """Scan only visible text in OPF spine documents.

    High-confidence findings make ``ok`` false. Medium-confidence findings
    remain warnings so legitimate English prose, code, and titles are not
    silently rejected.
    """

    findings: list[dict] = []
    warnings: list[dict] = []
    scanned_members: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()

    with zipfile.ZipFile(path) as zf:
        package = _package_path(zf)
        opf = ET.fromstring(zf.read(package))
        base = PurePosixPath(package).parent
        manifest: dict[str, tuple[str, str]] = {}
        spine: list[str] = []
        for node in opf.iter():
            kind = _local_name(node.tag)
            if kind == "item" and node.get("id") and node.get("href"):
                manifest[node.get("id") or ""] = (
                    _resolve_member(base, node.get("href") or ""),
                    node.get("media-type") or "",
                )
            elif kind == "itemref" and node.get("idref"):
                spine.append(node.get("idref") or "")

        for idref in spine:
            member, media_type = manifest.get(idref, ("", ""))
            if not member or (
                "html" not in media_type.lower()
                and not member.lower().endswith((".xhtml", ".html", ".htm"))
            ):
                continue
            root = ET.fromstring(zf.read(member))
            body = next(
                (node for node in root.iter() if _local_name(node.tag) == "body"), None
            )
            if body is None:
                continue
            scanned_members.append(member)
            for element in _candidate_elements(body):
                visible = _visible_text(element)
                if not visible:
                    continue
                anchor = _anchor(element)
                for issue in detect_translation_contamination(visible):
                    key = (member, issue.confidence, issue.rule, issue.excerpt)
                    if key in seen:
                        continue
                    seen.add(key)
                    record = {
                        "member": member,
                        "anchor": anchor,
                        **asdict(issue),
                    }
                    (findings if issue.confidence == "high" else warnings).append(
                        record
                    )

    return {
        "ok": not findings,
        "status": "passed" if not findings else "failed",
        "detector_version": CONTAMINATION_DETECTOR_VERSION,
        "scanned_spine_members": scanned_members,
        "findings": findings,
        "warnings": warnings,
    }
