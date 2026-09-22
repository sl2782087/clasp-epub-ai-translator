#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Check or install the pinned bilingual_book_maker dependency."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


BBOOK_MAKER_REVISION = "4e4e20cead3431e4880b505795a19adf1537ca1a"
BBOOK_MAKER_SPEC = (
    "git+https://github.com/sl2782087/bilingual_book_maker.git@"
    + BBOOK_MAKER_REVISION
)


def _program(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name in {"ebook-meta", "ebook-convert"}:
        candidates = [Path("/Applications/calibre.app/Contents/MacOS")]
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            value = os.environ.get(variable)
            if value:
                candidates.append(Path(value) / "Calibre2")
        for directory in candidates:
            for filename in (name, f"{name}.exe"):
                candidate = directory / filename
                if candidate.is_file():
                    return str(candidate)
    return None


def _font() -> str | None:
    override = os.environ.get("CLASP_EPUB_FONT")
    candidates = ([Path(override).expanduser()] if override else []) + [
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
    ]
    return next((str(path) for path in candidates if path.is_file()), None)


def diagnostics() -> dict:
    return {
        "python": {
            "ok": sys.version_info >= (3, 10),
            "version": ".".join(str(part) for part in sys.version_info[:3]),
        },
        "uv": {"ok": bool(_program("uv")), "path": _program("uv")},
        "bbook_maker": {
            "ok": bool(_program("bbook_maker")),
            "path": _program("bbook_maker"),
            "required_revision": BBOOK_MAKER_REVISION,
        },
        "calibre": {
            "optional": True,
            "ebook_meta": _program("ebook-meta"),
            "ebook_convert": _program("ebook-convert"),
        },
        "cjk_font": {
            "required_for_image_translation": True,
            "path": _font(),
            "override": "CLASP_EPUB_FONT",
        },
    }


def install() -> None:
    uv = _program("uv")
    if not uv:
        raise RuntimeError("uv was not found. Install uv from https://docs.astral.sh/uv/")
    subprocess.run(
        [uv, "tool", "install", "--force", BBOOK_MAKER_SPEC],
        check=True,
    )
    bin_result = subprocess.run(
        [uv, "tool", "dir", "--bin"],
        check=True,
        capture_output=True,
        text=True,
    )
    executable_name = "bbook_maker.exe" if os.name == "nt" else "bbook_maker"
    executable = Path(bin_result.stdout.strip()) / executable_name
    if not executable.is_file():
        found = _program("bbook_maker")
        if not found:
            raise RuntimeError(
                "Installation completed, but bbook_maker is not on PATH. "
                "Restart the terminal or add the uv tool bin directory to PATH."
            )
        executable = Path(found)
    subprocess.run([str(executable), "--help"], check=True, stdout=subprocess.DEVNULL)
    print(f"Installed pinned bilingual_book_maker revision {BBOOK_MAKER_REVISION}")
    print(f"Executable: {executable}")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument(
        "command",
        choices=("check", "install"),
        nargs="?",
        default="check",
        help="check the environment or explicitly install the pinned translator fork",
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            install()
        print(json.dumps(diagnostics(), ensure_ascii=False, indent=2))
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
