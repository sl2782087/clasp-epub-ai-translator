"""Carry an engine's source-bound review handoff through wrapper post-processing."""

import hashlib
import json
from pathlib import Path
import subprocess

REFERENCE_CONTEXT_VERSION = "epub-references-1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_engine(executable):
    result = subprocess.run(
        [executable, "--reference-context-version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode or result.stdout.strip().splitlines()[-1:] != [
        REFERENCE_CONTEXT_VERSION
    ]:
        raise ValueError(
            "The installed engine lacks the required EPUB reference/handoff protocol. "
            "Finish active translations before installing the skill's pinned engine."
        )


def read_handoff(source, generated):
    payload = json.loads(
        Path(generated).with_suffix(".review.json").read_text(encoding="utf-8")
    )
    if (
        payload.get("schema") != "bbm-review-handoff-1"
        or payload.get("reference_context_version") != REFERENCE_CONTEXT_VERSION
    ):
        raise ValueError("Unknown review handoff protocol")
    if payload.get("source_sha256") != sha256(source) or payload.get(
        "target_sha256"
    ) != sha256(generated):
        raise ValueError(
            "Review handoff does not match the original and generated EPUB"
        )
    if not isinstance(payload.get("units"), list):
        raise ValueError("Review handoff has no unit inventory")
    return payload


def publish_handoff(payload, final):
    destination = Path(final).with_suffix(".review.json")
    rebound = dict(payload)
    rebound["engine_target_sha256"] = payload["target_sha256"]
    rebound["target_sha256"] = sha256(final)
    rebound["postprocessing"] = (
        "Validated wrapper layout/image processing; source unit identities unchanged"
    )
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(rebound, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return destination
