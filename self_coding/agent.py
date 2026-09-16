"""Safe, provider-agnostic autonomous coding loop.

The module limits an agent to a clean Git repository, requires verification
after every coding pass, and restores the exact starting commit on failure.
It never executes commands through a shell.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


class SelfCodingError(RuntimeError):
    """Raised when a self-coding run cannot safely proceed."""


@dataclass(frozen=True)
class SelfCodingConfig:
    repo: Path
    test_commands: tuple[tuple[str, ...], ...] = ((sys.executable, "-m", "unittest", "discover", "-s", "tests"),)
    timeout_seconds: int = 900
    push_branch: bool = False
    max_passes: int = 1
    backend: str = "auto"


class SelfCodingAgent:
    """Run a cloud coding agent against this repository with Git guardrails."""

    def __init__(self, config: SelfCodingConfig) -> None:
        self.config = config
        self.repo = config.repo.resolve()
        if not self.repo.is_dir():
            raise SelfCodingError(f"Repository does not exist: {self.repo}")

    def _run(self, args: Sequence[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                list(args),
                cwd=self.repo,
                text=True,
                capture_output=True,
                check=False,
                timeout=timeout or self.config.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise SelfCodingError(f"Required executable is missing: {args[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise SelfCodingError(f"Command timed out: {' '.join(args)}") from exc

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self._run(("git", *args))

    def validate_repo(self) -> None:
        if not (self.repo / ".git").exists():
            raise SelfCodingError("Self-coding requires a real Git clone with a .git directory.")
        result = self._git("rev-parse", "--show-toplevel")
        if result.returncode != 0 or Path(result.stdout.strip()).resolve() != self.repo:
            raise SelfCodingError("Git repository root does not match the configured agent home.")

        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError(status.stderr.strip() or "Unable to inspect Git status.")
        if status.stdout.strip():
            raise SelfCodingError("Repository is not clean; refusing to overwrite existing work.")

    def _new_branch(self) -> tuple[str, str]:
        head = self._git("rev-parse", "HEAD")
        if head.returncode != 0:
            raise SelfCodingError("Unable to read the current Git commit.")
        baseline = head.stdout.strip()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch = f"agent/self-code/{stamp}"
        created = self._git("switch", "-c", branch)
        if created.returncode != 0:
            raise SelfCodingError(created.stderr.strip() or "Unable to create self-coding branch.")
        return branch, baseline

    @staticmethod
    def _prompt(goal: str) -> str:
        return f"""You are the implementation agent for this repository.

Goal: {goal}

Rules:
- Work ONLY inside the supplied Git repository.
- Read the existing code and documentation before changing anything.
- Preserve existing behavior unless the goal requires a change.
- Do not access, print, copy, or modify credentials, tokens, private keys, browser profiles, or files outside the repository.
- Do not weaken authentication, permissions, safety checks, tests, or rollback logic.
- Prefer small, reversible changes.
- Add or update tests for every behavioral change.
- Run the repository's relevant tests before declaring success.
- Never claim success when tests fail.
- Do not commit generated secrets or machine-specific configuration.

Implement the goal directly, then leave the repository in a clean, testable state."""

    def _find_backend(self) -> str:
        requested = self.config.backend.lower()
        if requested != "auto":
            if shutil.which(requested) is None:
                raise SelfCodingError(f"Configured coding backend is unavailable: {requested}")
            return requested
        for candidate in ("claude", "codex", "gemini"):
            if shutil.which(candidate):
                return candidate
        raise SelfCodingError("No supported cloud coding CLI was found (claude, codex, or gemini).")

    def _invoke_backend(self, goal: str) -> None:
        backend = self._find_backend()
        prompt = self._prompt(goal)
        if backend == "claude":
            args = (backend, "-p", prompt)
        elif backend == "codex":
            args = (backend, "exec", prompt)
        else:
            args = (backend, "-p", prompt)
        result = self._run(args)
        if result.returncode != 0:
            raise SelfCodingError(result.stderr.strip() or result.stdout.strip() or f"{backend} exited with code {result.returncode}.")

    def _verify(self) -> None:
        for command in self.config.test_commands:
            result = self._run(command)
            if result.returncode != 0:
                output = (result.stdout + "\n" + result.stderr).strip()
                raise SelfCodingError(f"Verification failed for {' '.join(command)}.\n{output[-12000:]}")

        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError("Unable to verify the post-test Git state.")

    def _rollback(self, baseline: str) -> None:
        reset = self._git("reset", "--hard", baseline)
        if reset.returncode != 0:
            raise SelfCodingError(reset.stderr.strip() or "Rollback failed while resetting the repository.")

        clean = self._git("clean", "-fd")
        if clean.returncode != 0:
            raise SelfCodingError(clean.stderr.strip() or "Rollback failed while cleaning untracked files.")

        status = self._git("status", "--porcelain")
        if status.returncode != 0:
            raise SelfCodingError(status.stderr.strip() or "Rollback verification failed while checking Git status.")
        if status.stdout.strip():
            raise SelfCodingError("Rollback verification failed: repository is still dirty.")

    def run(self, goal: str) -> str:
        """Implement one or more safe passes and return the resulting branch."""
        if not goal.strip():
            raise SelfCodingError("A non-empty coding goal is required.")
        if self.config.max_passes < 1:
            raise SelfCodingError("max_passes must be at least 1.")

        self.validate_repo()
        branch, baseline = self._new_branch()

        try:
            for _ in range(self.config.max_passes):
                self._invoke_backend(goal)
                self._verify()
                status = self._git("status", "--porcelain")
                if not status.stdout.strip():
                    raise SelfCodingError("Coding agent completed without producing a change.")
                staged = self._git("add", "--all")
                if staged.returncode != 0:
                    raise SelfCodingError(staged.stderr.strip() or "Unable to stage changes.")
                committed = self._git("commit", "-m", "agent: verified self-coding change")
                if committed.returncode != 0:
                    raise SelfCodingError(committed.stderr.strip() or "Unable to commit verified changes.")

            if self.config.push_branch:
                pushed = self._git("push", "-u", "origin", branch)
                if pushed.returncode != 0:
                    raise SelfCodingError(pushed.stderr.strip() or "Unable to push self-coding branch.")
            return branch
        except Exception:
            self._rollback(baseline)
            raise
