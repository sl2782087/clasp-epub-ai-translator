from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import epub_translate  # noqa: E402


class TerminalConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.settings = base / "settings.json"
        self.credentials = base / "credentials.json"
        self.glossary = base / "glossary.txt"
        initial = dict(epub_translate.DEFAULT_SETTINGS)
        initial.update({"engine": "openai", "model": "existing-model", "calibre": "none"})
        self.settings.write_text(json.dumps(initial), encoding="utf-8")
        self.path_patches = (
            mock.patch.object(epub_translate, "settings_path", return_value=self.settings),
            mock.patch.object(
                epub_translate, "credentials_path", return_value=self.credentials
            ),
            mock.patch.object(epub_translate, "glossary_path", return_value=self.glossary),
        )
        for patcher in self.path_patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    @staticmethod
    def blank_input(_prompt: str) -> str:
        return ""

    def test_hidden_key_is_saved_but_never_printed(self) -> None:
        output: list[str] = []
        result = epub_translate.run_terminal_configuration(
            input_fn=self.blank_input,
            secret_fn=lambda _prompt: "top-secret-value",
            output_fn=output.append,
        )

        self.assertEqual(result["engine"], "openai")
        self.assertEqual(
            json.loads(self.credentials.read_text(encoding="utf-8"))["openai"],
            "top-secret-value",
        )
        self.assertNotIn("top-secret-value", "\n".join(output))
        self.assertEqual(self.credentials.stat().st_mode & 0o777, 0o600)

    def test_blank_key_preserves_saved_credential(self) -> None:
        self.credentials.write_text(
            json.dumps({"openai": "already-saved"}), encoding="utf-8"
        )
        epub_translate.run_terminal_configuration(
            input_fn=self.blank_input,
            secret_fn=lambda _prompt: "",
            output_fn=lambda _line: None,
        )
        self.assertEqual(
            json.loads(self.credentials.read_text(encoding="utf-8"))["openai"],
            "already-saved",
        )

    def test_model_discovery_can_select_returned_model(self) -> None:
        choose_model = False

        def answer(prompt: str) -> str:
            nonlocal choose_model
            if "拉取支持的模型列表" in prompt:
                choose_model = True
                return "y"
            if choose_model and "输入编号或值" in prompt:
                choose_model = False
                return "2"
            return ""

        with mock.patch.object(
            epub_translate,
            "provider_models",
            return_value={
                "ok": True,
                "models": ["model-a", "model-b"],
                "message": "two models",
            },
        ):
            result = epub_translate.run_terminal_configuration(
                input_fn=answer,
                secret_fn=lambda _prompt: "",
                output_fn=lambda _line: None,
            )

        self.assertEqual(result["model"], "model-b")

    def test_manual_glossary_entry_is_normalized(self) -> None:
        answers = iter(["3", "真壁 -> 真壁", "時刻表 -> 时刻表 # fixed", ""])
        text, count = epub_translate.terminal_glossary(
            "", input_fn=lambda _prompt: next(answers), output_fn=lambda _line: None
        )
        self.assertEqual(count, 2)
        self.assertIn("真壁 -> 真壁", text)
        self.assertTrue(text.endswith("\n"))

    def test_terminal_cli_rejects_non_tty_input(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "epub_translate.py"), "configure", "--terminal"],
            input="",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires an interactive TTY", result.stderr)

    def test_skill_directly_links_complete_hermes_bundle(self) -> None:
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        required = [
            "scripts/bootstrap.py",
            "scripts/epub_translate.py",
            "scripts/translation_guard.py",
            "scripts/epub_image_translate.py",
            "scripts/epub_images.py",
            "scripts/audit_regions.py",
            "scripts/optimize_png.py",
            "references/options.md",
            "references/hermes-agent.md",
            "references/image-workflow.md",
            "references/image-artwork.md",
            "references/image-precision.md",
            "references/image-compression.md",
        ]
        for relative in required:
            with self.subTest(relative=relative):
                self.assertIn(f"]({relative})", skill_text)


if __name__ == "__main__":
    unittest.main()
