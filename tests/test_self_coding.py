from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from self_coding.agent import SelfCodingAgent, SelfCodingConfig, SelfCodingError


class SelfCodingTests(unittest.TestCase):
    def make_repo(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fullstack-agent-selfcoding-"))
        subprocess.run(("git", "init", "-b", "main"), cwd=root, check=True, capture_output=True, text=True)
        subprocess.run(("git", "config", "user.name", "Self Coding Test"), cwd=root, check=True)
        subprocess.run(("git", "config", "user.email", "self-coding-test@example.invalid"), cwd=root, check=True)
        (root / "README.md").write_text("seed\n", encoding="utf-8")
        subprocess.run(("git", "add", "README.md"), cwd=root, check=True)
        subprocess.run(("git", "commit", "-m", "seed"), cwd=root, check=True, capture_output=True, text=True)
        return root

    def test_dirty_repository_is_rejected(self) -> None:
        root = self.make_repo()
        (root / "dirty.txt").write_text("existing work\n", encoding="utf-8")
        with self.assertRaisesRegex(SelfCodingError, "not clean"):
            SelfCodingAgent(SelfCodingConfig(repo=root)).validate_repo()

    def test_failed_verification_rolls_back_changes(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(
            repo=root,
            test_commands=((sys.executable, "-c", "raise SystemExit(1)"),),
        )
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "generated.txt").write_text("must disappear\n", encoding="utf-8")  # type: ignore[method-assign]

        with self.assertRaises(SelfCodingError):
            agent.run("make a safe change")

        self.assertFalse((root / "generated.txt").exists())
        status = subprocess.run(("git", "status", "--porcelain"), cwd=root, check=True, capture_output=True, text=True)
        self.assertEqual(status.stdout, "")

    def test_rollback_failure_is_reported(self) -> None:
        root = self.make_repo()
        agent = SelfCodingAgent(SelfCodingConfig(repo=root))

        def failed_git(*args: str) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["git", *args], 1, "", "reset failed")

        agent._git = failed_git  # type: ignore[method-assign]
        with self.assertRaisesRegex(SelfCodingError, "Rollback failed while resetting"):
            agent._rollback("deadbeef")

    def test_successful_pass_is_committed(self) -> None:
        root = self.make_repo()
        config = SelfCodingConfig(
            repo=root,
            test_commands=((sys.executable, "-c", "print('ok')"),),
        )
        agent = SelfCodingAgent(config)
        agent._invoke_backend = lambda goal: (root / "verified.txt").write_text("verified\n", encoding="utf-8")  # type: ignore[method-assign]

        branch = agent.run("make a verified change")
        self.assertTrue(branch.startswith("agent/self-code/"))
        self.assertEqual((root / "verified.txt").read_text(encoding="utf-8"), "verified\n")
        log = subprocess.run(("git", "log", "-1", "--pretty=%s"), cwd=root, check=True, capture_output=True, text=True)
        self.assertEqual(log.stdout.strip(), "agent: verified self-coding change")


if __name__ == "__main__":
    unittest.main()
