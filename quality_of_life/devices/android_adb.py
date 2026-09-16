"""Optional direct provider for physical Android devices over ADB.

ADB is used only when the user has an authorized Android device and adb is
available. No emulator is required. scrcpy is an optional companion for a live
interactive screen. The optional Jarvis Android companion adds notification and
accessibility-backed phone-native actions through an ADB-local forward.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import replace

from .android_companion import AndroidCompanionClient
from .models import DeviceCapability, DeviceResult, DeviceState
from .provider import DeviceInputEvent, FileTransferDirection


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


class AndroidAdbProvider:
    name = "android-adb"

    def __init__(
        self,
        adb: str | None = None,
        scrcpy: str | None = None,
        runner: Runner | None = None,
        enable_companion: bool = True,
        companion: AndroidCompanionClient | None = None,
    ):
        self.adb = adb or shutil.which("adb")
        self.scrcpy = scrcpy or shutil.which("scrcpy")
        self._runner = runner or self._run
        self.companion = companion if companion is not None else (
            AndroidCompanionClient(self.adb, runner=self._runner) if enable_companion else None
        )

    @staticmethod
    def _run(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, check=False)

    def _adb(self, *args: str) -> DeviceResult | subprocess.CompletedProcess[str]:
        if not self.adb:
            return DeviceResult.failure("UNAVAILABLE", "adb is not installed or not on PATH")
        try:
            return self._runner((self.adb, *args))
        except OSError as exc:
            return DeviceResult.failure("UNAVAILABLE", f"adb could not start: {exc}")

    @staticmethod
    def _parse_devices(output: str) -> tuple[DeviceState, ...]:
        devices: list[DeviceState] = []
        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices attached"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, status = parts[0], parts[1]
            devices.append(DeviceState(device_id=serial, label=serial, connected=status == "device", provider=AndroidAdbProvider.name))
        return tuple(devices)

    def list_devices(self) -> Sequence[DeviceState]:
        result = self._adb("devices")
        if isinstance(result, DeviceResult):
            return ()
        return self._parse_devices(result.stdout)

    def _state(self, device_id: str) -> DeviceState | None:
        return next((d for d in self.list_devices() if d.device_id == device_id), None)

    def get_state(self, device_id: str) -> DeviceResult:
        base = self._state(device_id)
        if base is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not connected through adb")
        if not base.connected:
            return DeviceResult.failure("DISCONNECTED", "Device is not ready")
        result = self._adb("-s", device_id, "shell", "dumpsys", "battery")
        if isinstance(result, DeviceResult):
            return result
        level = None
        status = None
        for line in result.stdout.splitlines():
            key, _, value = line.strip().partition(":")
            if key == "level":
                try:
                    level = int(value.strip())
                except ValueError:
                    level = None
            elif key == "status":
                try:
                    status = int(value.strip())
                except ValueError:
                    status = None
        charging = status in {2, 5} if status is not None else None
        return DeviceResult.success("device state available", state=replace(base, battery_percent=level, charging=charging))

    def _companion_available(self, device_id: str) -> bool:
        if self.companion is None:
            return False
        try:
            return self.companion.health(device_id).ok
        except Exception:
            return False

    def capabilities(self, device_id: str) -> frozenset[DeviceCapability]:
        state = self._state(device_id)
        if state is None:
            return frozenset()
        capabilities = {
            DeviceCapability.STATE_READ,
            DeviceCapability.INPUT_CONTROL,
            DeviceCapability.FILES,
            DeviceCapability.APP_CONTROL,
        }
        if self.scrcpy:
            capabilities.add(DeviceCapability.SCREEN_VIEW)
        if self._companion_available(device_id):
            capabilities.add(DeviceCapability.NOTIFICATION_READ)
        return frozenset(capabilities)

    def display_size(self, device_id: str) -> tuple[int, int] | None:
        state = self._state(device_id)
        if state is None or not state.connected:
            return None
        result = self._adb("-s", device_id, "shell", "wm", "size")
        if isinstance(result, DeviceResult) or result.returncode != 0:
            return None
        matches = re.findall(r"(\d+)x(\d+)", result.stdout)
        if not matches:
            return None
        width, height = map(int, matches[-1])
        return (width, height) if width > 0 and height > 0 else None

    def _command(self, device_id: str, *args: str) -> DeviceResult:
        state = self._state(device_id)
        if state is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not connected through adb")
        if not state.connected:
            return DeviceResult.failure("DISCONNECTED", "Device is not ready")
        result = self._adb("-s", device_id, *args)
        if isinstance(result, DeviceResult):
            return result
        if result.returncode != 0:
            return DeviceResult.failure("DEVICE_ERROR", result.stderr.strip() or "adb command failed")
        return DeviceResult.success("device command completed", stdout=result.stdout)

    def view_screen(self, device_id: str) -> DeviceResult:
        if not self.scrcpy:
            return DeviceResult.failure("UNAVAILABLE", "scrcpy is not installed; live device view is unavailable")
        state = self._state(device_id)
        if state is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not connected through adb")
        if not state.connected:
            return DeviceResult.failure("DISCONNECTED", "Device is not ready")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if platform.system() == "Windows" else 0
        try:
            subprocess.Popen((self.scrcpy, "--serial", device_id), creationflags=creationflags)
        except OSError as exc:
            return DeviceResult.failure("UNAVAILABLE", f"scrcpy could not start: {exc}")
        return DeviceResult.success("live device view started", device_id=device_id)

    def send_input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult:
        if event.kind == "tap":
            if event.x is None or event.y is None:
                return DeviceResult.failure("INVALID", "tap requires x and y")
            return self._command(device_id, "shell", "input", "tap", str(int(event.x)), str(int(event.y)))
        if event.kind == "swipe":
            if event.x is None or event.y is None or event.amount is None:
                return DeviceResult.failure("INVALID", "swipe requires x, y, and amount")
            return self._command(device_id, "shell", "input", "swipe", str(int(event.x)), str(int(event.y)), str(int(event.x + event.amount)), str(int(event.y)))
        if event.kind == "text":
            if event.text is None:
                return DeviceResult.failure("INVALID", "text input requires text")
            encoded = event.text.replace("%", "%25").replace(" ", "%s")
            return self._command(device_id, "shell", "input", "text", encoded)
        if event.kind == "back":
            return self._command(device_id, "shell", "input", "keyevent", "4")
        if event.kind == "home":
            return self._command(device_id, "shell", "input", "keyevent", "3")
        if event.kind == "recent":
            return self._command(device_id, "shell", "input", "keyevent", "187")
        return DeviceResult.failure("UNSUPPORTED", f"Unsupported input event: {event.kind}")

    def read_notifications(self, device_id: str) -> DeviceResult:
        if self.companion is None:
            return DeviceResult.failure("UNAVAILABLE", "Jarvis Android companion is not configured")
        result = self.companion.notifications(device_id)
        return result

    def transfer_file(self, device_id: str, direction: FileTransferDirection, path: str) -> DeviceResult:
        if not path.strip():
            return DeviceResult.failure("INVALID", "path must not be empty")
        if direction is FileTransferDirection.TO_DEVICE:
            return self._command(device_id, "push", path, "/sdcard/")
        if direction is FileTransferDirection.FROM_DEVICE:
            return self._command(device_id, "pull", path, os.getcwd())
        return DeviceResult.failure("INVALID", "unknown transfer direction")

    def open_app(self, device_id: str, app_id: str) -> DeviceResult:
        if not app_id.strip():
            return DeviceResult.failure("INVALID", "app_id must not be empty")
        return self._command(device_id, "shell", "monkey", "-p", app_id, "1")

    def close(self) -> None:
        if self.companion is not None:
            self.companion.close()
