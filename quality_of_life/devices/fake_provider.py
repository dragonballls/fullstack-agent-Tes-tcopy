"""Deterministic phone provider for unit and integration tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .models import DeviceCapability, DeviceResult, DeviceState
from .provider import DeviceInputEvent, FileTransferDirection


@dataclass
class FakePhoneProvider:
    name: str = "fake"
    devices: dict[str, DeviceState] = field(default_factory=dict)
    device_capabilities: dict[str, frozenset[DeviceCapability]] = field(default_factory=dict)
    device_sizes: dict[str, tuple[int, int]] = field(default_factory=dict)
    operations: list[tuple[str, str, object | None]] = field(default_factory=list)

    def add_device(
        self,
        state: DeviceState,
        capabilities: frozenset[DeviceCapability] | None = None,
        display_size: tuple[int, int] = (1080, 1920),
    ) -> None:
        self.devices[state.device_id] = state
        self.device_capabilities[state.device_id] = capabilities or frozenset({DeviceCapability.STATE_READ})
        self.device_sizes[state.device_id] = display_size

    def list_devices(self) -> Sequence[DeviceState]:
        return tuple(self.devices.values())

    def _get(self, device_id: str) -> DeviceState | None:
        return self.devices.get(device_id)

    def get_state(self, device_id: str) -> DeviceResult:
        state = self._get(device_id)
        if state is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        return DeviceResult.success("state available", state=state)

    def capabilities(self, device_id: str) -> frozenset[DeviceCapability]:
        return self.device_capabilities.get(device_id, frozenset())

    def display_size(self, device_id: str) -> tuple[int, int] | None:
        return self.device_sizes.get(device_id)

    def _require_connected(self, device_id: str) -> DeviceResult | None:
        state = self._get(device_id)
        if state is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        if not state.connected:
            return DeviceResult.failure("DISCONNECTED", "Device is disconnected")
        return None

    def _require_capability(self, device_id: str, capability: DeviceCapability) -> DeviceResult | None:
        if capability not in self.capabilities(device_id):
            return DeviceResult.failure("UNAVAILABLE", f"Capability is unavailable: {capability.value}")
        return None

    def view_screen(self, device_id: str) -> DeviceResult:
        for failure in (self._require_connected(device_id), self._require_capability(device_id, DeviceCapability.SCREEN_VIEW)):
            if failure is not None:
                return failure
        self.operations.append(("screen", device_id, None))
        return DeviceResult.success("screen available", device_id=device_id)

    def send_input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult:
        for failure in (self._require_connected(device_id), self._require_capability(device_id, DeviceCapability.INPUT_CONTROL)):
            if failure is not None:
                return failure
        self.operations.append(("input", device_id, event))
        return DeviceResult.success("input dispatched")

    def read_notifications(self, device_id: str) -> DeviceResult:
        for failure in (self._require_connected(device_id), self._require_capability(device_id, DeviceCapability.NOTIFICATION_READ)):
            if failure is not None:
                return failure
        self.operations.append(("notifications", device_id, None))
        return DeviceResult.success("notifications available", notifications=[])

    def transfer_file(self, device_id: str, direction: FileTransferDirection, path: str) -> DeviceResult:
        for failure in (self._require_connected(device_id), self._require_capability(device_id, DeviceCapability.FILES)):
            if failure is not None:
                return failure
        self.operations.append(("file", device_id, (direction, path)))
        return DeviceResult.success("file transfer dispatched", path=path)

    def open_app(self, device_id: str, app_id: str) -> DeviceResult:
        for failure in (self._require_connected(device_id), self._require_capability(device_id, DeviceCapability.APP_CONTROL)):
            if failure is not None:
                return failure
        if not app_id.strip():
            return DeviceResult.failure("INVALID", "app_id must not be empty")
        self.operations.append(("app", device_id, app_id))
        return DeviceResult.success("app launch dispatched", app_id=app_id)

    def close(self) -> None:
        self.operations.append(("close", "", None))
