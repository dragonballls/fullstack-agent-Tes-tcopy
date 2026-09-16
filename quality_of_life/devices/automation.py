"""Cancellable automation runners for physical devices."""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable, Mapping

from ..permissions import Capability, CapabilityPolicy
from .facade import DeviceFacade
from .models import DeviceResult
from .provider import DeviceInputEvent


class DeviceAutomation:
    def __init__(self, facade: DeviceFacade, policy: CapabilityPolicy) -> None:
        self.facade = facade
        self.policy = policy

    def run(
        self,
        device_id: str,
        action: Callable[[threading.Event], DeviceResult],
        cancel: threading.Event | None = None,
    ) -> DeviceResult:
        self.policy.check(Capability.DEVICE_AUTOMATION)
        token = cancel or threading.Event()
        state = self.facade.state(device_id)
        if not state.ok:
            return state
        current = state.data.get("state")
        if current is not None and not current.connected:
            return DeviceResult.failure("DISCONNECTED", "Device is disconnected")
        if token.is_set():
            return DeviceResult.failure("CANCELLED", "Device automation was cancelled")
        try:
            result = action(token)
        except Exception as exc:
            return DeviceResult.failure("PROVIDER_ERROR", f"Device automation failed: {exc}")
        if token.is_set():
            return DeviceResult.failure("CANCELLED", "Device automation was cancelled")
        refreshed = self.facade.state(device_id)
        if refreshed.ok:
            latest = refreshed.data.get("state")
            if latest is not None and not latest.connected:
                return DeviceResult.failure("DISCONNECTED", "Device disconnected during automation")
        return result

    def run_steps(
        self,
        device_id: str,
        steps: Iterable[Mapping[str, object]],
        cancel: threading.Event | None = None,
        confirmed: bool = False,
    ) -> DeviceResult:
        """Execute a small declarative input sequence on one device.

        Supported steps intentionally stay limited to device UI input. This
        keeps automation deterministic and lets higher-level Jarvis planning
        compose safe tasks from a fixed vocabulary.
        """
        normalized = [dict(step) for step in steps]
        if not normalized:
            return DeviceResult.failure("INVALID", "automation requires at least one step")

        def action(token: threading.Event) -> DeviceResult:
            for index, step in enumerate(normalized, start=1):
                if token.is_set():
                    return DeviceResult.failure("CANCELLED", "Device automation was cancelled")
                kind = str(step.get("kind", "")).strip()
                if kind not in {"tap", "swipe", "text", "back", "home", "recent"}:
                    return DeviceResult.failure("UNSUPPORTED", f"Unsupported automation step {index}: {kind}")
                event = DeviceInputEvent(
                    kind,
                    x=float(step["x"]) if step.get("x") is not None else None,
                    y=float(step["y"]) if step.get("y") is not None else None,
                    text=str(step["text"]) if step.get("text") is not None else None,
                    amount=float(step["amount"]) if step.get("amount") is not None else None,
                )
                result = self.facade.input(device_id, event, confirmed=confirmed)
                if not result.ok:
                    return DeviceResult.failure(
                        result.code,
                        f"Automation step {index} failed: {result.message}",
                    )
            return DeviceResult.success("device automation completed", steps=len(normalized))

        return self.run(device_id, action, cancel)
