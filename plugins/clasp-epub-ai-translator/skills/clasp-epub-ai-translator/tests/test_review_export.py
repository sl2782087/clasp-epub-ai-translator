import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import tempfile

spec = importlib.util.spec_from_file_location(
    "review_export", Path(__file__).parents[1] / "scripts/review_export.py"
)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)


class ReviewExportTests(unittest.TestCase):
    def test_rebind_keeps_source_and_records_both_target_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, generated, final = [
                root / name for name in ("source.epub", "generated.epub", "final.epub")
            ]
            for path in (source, generated, final):
                path.write_bytes(path.name.encode())
            payload = {
                "schema": "bbm-review-handoff-1",
                "reference_context_version": review.REFERENCE_CONTEXT_VERSION,
                "source_sha256": review.sha256(source),
                "target_sha256": review.sha256(generated),
                "units": [{"id": "stable"}],
            }
            generated.with_suffix(".review.json").write_text(json.dumps(payload))
            parsed = review.read_handoff(source, generated)
            dest = review.publish_handoff(parsed, final)
            result = json.loads(dest.read_text())
            self.assertEqual(result["engine_target_sha256"], review.sha256(generated))
            self.assertEqual(result["target_sha256"], review.sha256(final))
            self.assertEqual(result["units"], payload["units"])
            self.assertEqual(parsed, payload)
            with self.assertRaises(FileExistsError):
                review.publish_handoff(parsed, final)
            source.write_bytes(b"changed")
            with self.assertRaises(ValueError):
                review.read_handoff(source, generated)

    def test_engine_probe_accepts_leading_dependency_notice(self):
        result = SimpleNamespace(
            returncode=0,
            stdout="dependency notice\n" + review.REFERENCE_CONTEXT_VERSION + "\n",
        )
        with patch.object(review.subprocess, "run", return_value=result):
            review.require_engine("bbook_maker")

    def test_old_engine_fails_before_translation(self):
        with patch.object(
            review.subprocess,
            "run",
            return_value=SimpleNamespace(returncode=2, stdout=""),
        ) as run:
            with self.assertRaisesRegex(ValueError, "Finish active translations"):
                review.require_engine("bbook_maker")
            self.assertEqual(
                run.call_args.args[0], ["bbook_maker", "--reference-context-version"]
            )


if __name__ == "__main__":
    unittest.main()
