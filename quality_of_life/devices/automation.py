"""Small cancellable automation runner for physical devices."""

from __future__ import annotations

import threading
from collections.abc import Callable

from ..permissions import Capability, CapabilityPolicy
from .facade import DeviceFacade
from .models import DeviceResult


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
