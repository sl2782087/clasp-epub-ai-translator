from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bootstrap  # noqa: E402


class BootstrapTests(unittest.TestCase):
    def test_dependency_is_pinned_to_exact_fork_revision(self) -> None:
        self.assertIn("sl2782087/bilingual_book_maker", bootstrap.BBOOK_MAKER_SPEC)
        self.assertTrue(bootstrap.BBOOK_MAKER_SPEC.endswith(bootstrap.BBOOK_MAKER_REVISION))
        self.assertEqual(len(bootstrap.BBOOK_MAKER_REVISION), 40)

    def test_install_uses_uv_tool_and_verifies_executable(self) -> None:
        completed = mock.Mock(stdout="/tmp/uv-bin\n")
        with mock.patch.object(bootstrap, "_program", side_effect=["/usr/bin/uv"]), mock.patch.object(
            bootstrap.subprocess, "run", side_effect=[mock.Mock(), completed, mock.Mock()]
        ) as run, mock.patch.object(Path, "is_file", return_value=True):
            bootstrap.install()

        self.assertEqual(
            run.call_args_list[0].args[0],
            ["/usr/bin/uv", "tool", "install", "--force", bootstrap.BBOOK_MAKER_SPEC],
        )
        self.assertEqual(run.call_args_list[2].args[0], ["/tmp/uv-bin/bbook_maker", "--help"])


if __name__ == "__main__":
    unittest.main()
