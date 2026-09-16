"""Concurrent low-latency scrcpy session management for physical Android devices."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from .models import DeviceResult


class MirrorProcess(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int | None: ...


Launcher = Callable[[Sequence[str]], MirrorProcess]


@dataclass(frozen=True)
class MirrorSession:
    device_id: str
    label: str
    process: MirrorProcess


class MultiDeviceMirrorManager:
    """Own one independent scrcpy process per physical device.

    The manager deliberately does not relay or re-encode video through Python.
    Each phone gets its own scrcpy connection, addressed by its opaque device
    serial, which keeps screen transport independent across multiple phones.
    """

    def __init__(
        self,
        scrcpy: str | None,
        launcher: Launcher | None = None,
        *,
        low_latency: bool = True,
        window_layout: Sequence[tuple[int, int, int, int]] | None = None,
        stop_timeout: float = 2.0,
    ) -> None:
        self.scrcpy = scrcpy
        self._launcher = launcher or self._launch
        self._low_latency = low_latency
        self._window_layout = tuple(window_layout or ())
        self._stop_timeout = max(0.1, float(stop_timeout))
        self._sessions: dict[str, MirrorSession] = {}

    @staticmethod
    def _launch(args: Sequence[str]) -> MirrorProcess:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system() == "Windows" else 0
        return subprocess.Popen(tuple(args), creationflags=creationflags)

    @staticmethod
    def _window_args(layout: tuple[int, int, int, int] | None) -> tuple[str, ...]:
        if layout is None:
            return ()
        x, y, width, height = layout
        if width <= 0 or height <= 0:
            raise ValueError("mirror window width and height must be positive")
        return (
            f"--window-x={int(x)}",
            f"--window-y={int(y)}",
            f"--window-width={int(width)}",
            f"--window-height={int(height)}",
        )

    def _args(self, device_id: str, label: str, slot: int | None) -> tuple[str, ...]:
        args: list[str] = [self.scrcpy or "scrcpy", "--serial", device_id, f"--window-title=Jarvis — {label}"]
        if self._low_latency:
            # H.264 is documented by scrcpy as lower-latency than H.265.
            args.extend(("--video-codec=h264", "--max-fps=60"))
        layout = self._window_layout[slot] if slot is not None and slot < len(self._window_layout) else None
        args.extend(self._window_args(layout))
        return tuple(args)

    def _remove_stale(self, device_id: str) -> None:
        session = self._sessions.get(device_id)
        if session is None:
            return
        if session.process.poll() is None:
            return
        self._sessions.pop(device_id, None)

    def _slot_for(self, device_id: str) -> int | None:
        active = tuple(self._sessions)
        if device_id in active:
            return active.index(device_id)
        return len(active)

    def start(self, device_id: str, label: str | None = None) -> DeviceResult:
        device_id = device_id.strip()
        if not device_id:
            return DeviceResult.failure("INVALID", "device_id must not be empty")
        if not self.scrcpy:
            return DeviceResult.failure("UNAVAILABLE", "scrcpy is not installed; live device view is unavailable")

        self._remove_stale(device_id)
        existing = self._sessions.get(device_id)
        if existing is not None and existing.process.poll() is None:
            return DeviceResult.success(
                "live device view already running",
                device_id=device_id,
                pid=existing.process.pid,
            )

        display_label = (label or device_id).strip() or device_id
        slot = self._slot_for(device_id)
        try:
            process = self._launcher(self._args(device_id, display_label, slot))
        except (OSError, ValueError) as exc:
            return DeviceResult.failure("UNAVAILABLE", f"scrcpy could not start: {exc}")

        self._sessions[device_id] = MirrorSession(device_id=device_id, label=display_label, process=process)
        return DeviceResult.success("live device view started", device_id=device_id, pid=process.pid)

    def get(self, device_id: str) -> MirrorSession | None:
        self._remove_stale(device_id)
        return self._sessions.get(device_id)

    def active_ids(self) -> tuple[str, ...]:
        for device_id in tuple(self._sessions):
            self._remove_stale(device_id)
        return tuple(self._sessions)

    def stop(self, device_id: str) -> DeviceResult:
        session = self._sessions.pop(device_id, None)
        if session is None:
            return DeviceResult.success("live device view already stopped", device_id=device_id)
        if session.process.poll() is None:
            try:
                session.process.terminate()
                session.process.wait(timeout=self._stop_timeout)
            except (OSError, TimeoutError):
                return DeviceResult.failure("TIMEOUT", "scrcpy did not stop within the configured timeout")
        return DeviceResult.success("live device view stopped", device_id=device_id)

    def stop_all(self) -> tuple[DeviceResult, ...]:
        return tuple(self.stop(device_id) for device_id in tuple(self._sessions))
