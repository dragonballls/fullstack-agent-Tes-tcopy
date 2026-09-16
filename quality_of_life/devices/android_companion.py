"""Client for the optional Jarvis Android companion over ADB port forwarding."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence

from .models import DeviceResult


class AndroidCompanionClient:
    """Talk to the companion on the actual phone through ADB forwarding.

    Each physical phone gets its own PC-local forwarded port, while the Android
    service itself remains bound only to the phone's loopback interface.
    """

    DEVICE_PORT = 18765

    def __init__(
        self,
        adb: str | None,
        runner: Callable[[Sequence[str]], subprocess.CompletedProcess[str]] | None = None,
        opener: Callable[..., object] | None = None,
        port_base: int = 18765,
    ) -> None:
        self.adb = adb
        self._runner = runner or self._run
        self._opener = opener or urllib.request.urlopen
        self._port_base = port_base
        self._ports: dict[str, int] = {}
        self._next_port = port_base

    @staticmethod
    def _run(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, capture_output=True, text=True, check=False)

    def _local_port(self, device_id: str) -> int:
        if device_id not in self._ports:
            self._ports[device_id] = self._next_port
            self._next_port += 1
        return self._ports[device_id]

    def _forward(self, device_id: str) -> DeviceResult:
        if not self.adb:
            return DeviceResult.failure("UNAVAILABLE", "adb is not installed or not on PATH")
        local = self._local_port(device_id)
        try:
            result = self._runner((self.adb, "-s", device_id, "forward", f"tcp:{local}", f"tcp:{self.DEVICE_PORT}"))
        except OSError as exc:
            return DeviceResult.failure("UNAVAILABLE", f"adb forward failed: {exc}")
        if result.returncode != 0:
            return DeviceResult.failure("UNAVAILABLE", result.stderr.strip() or "adb forward failed")
        return DeviceResult.success("companion forwarded", port=local)

    def request(self, device_id: str, method: str, path: str, payload: dict[str, object] | None = None, timeout: float = 2.0) -> DeviceResult:
        forwarded = self._forward(device_id)
        if not forwarded.ok:
            return forwarded
        port = int(forwarded.data["port"])
        body = b""
        headers = {"Content-Type": "application/json"}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=body if body else None, headers=headers, method=method)
        try:
            with self._opener(request, timeout=timeout) as response:
                raw = response.read(1_000_000).decode("utf-8")
            data = json.loads(raw)
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            return DeviceResult.failure("UNAVAILABLE", f"companion request failed: {exc}")
        if not isinstance(data, dict):
            return DeviceResult.failure("INVALID", "companion returned a non-object response")
        if not bool(data.get("ok")):
            return DeviceResult.failure(str(data.get("code", "ERROR")), str(data.get("message", "companion request failed")), response=data)
        return DeviceResult.success(str(data.get("message", "companion request completed")), **data)

    def health(self, device_id: str) -> DeviceResult:
        return self.request(device_id, "GET", "/health")

    def notifications(self, device_id: str) -> DeviceResult:
        return self.request(device_id, "GET", "/notifications")

    def action(self, device_id: str, action: str, **payload: object) -> DeviceResult:
        return self.request(device_id, "POST", "/action", {"action": action, **payload})

    def close(self, device_id: str | None = None) -> None:
        if not self.adb:
            return
        items = ((device_id, self._ports.get(device_id)),) if device_id else tuple(self._ports.items())
        for serial, port in items:
            if not serial or port is None:
                continue
            try:
                self._runner((self.adb, "-s", serial, "forward", "--remove", f"tcp:{port}"))
            except OSError:
                pass
            self._ports.pop(serial, None)
