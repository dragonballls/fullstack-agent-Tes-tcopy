"""Phone Link integration boundary.

Phone Link is treated as a Windows-side transport. The bridge is injected so
CI and non-Windows environments do not depend on Microsoft Phone Link being
installed or running. A concrete Windows bridge can be supplied later without
changing the provider-neutral device API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .models import DeviceCapability, DeviceResult, DeviceState
from .provider import DeviceInputEvent, FileTransferDirection


class PhoneLinkBridge(Protocol):
    def list_devices(self) -> Sequence[DeviceState]: ...
    def state(self, device_id: str) -> DeviceResult: ...
    def screen(self, device_id: str) -> DeviceResult: ...
    def input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult: ...
    def notifications(self, device_id: str) -> DeviceResult: ...
    def transfer(self, device_id: str, direction: FileTransferDirection, path: str) -> DeviceResult: ...
    def open_app(self, device_id: str, app_id: str) -> DeviceResult: ...
    def close(self) -> None: ...


@dataclass
class UnavailablePhoneLinkBridge:
    reason: str = "No Phone Link bridge is configured"

    def list_devices(self) -> Sequence[DeviceState]:
        return ()

    def state(self, device_id: str) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def screen(self, device_id: str) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def notifications(self, device_id: str) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def transfer(self, device_id: str, direction: FileTransferDirection, path: str) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def open_app(self, device_id: str, app_id: str) -> DeviceResult:
        return DeviceResult.failure("UNAVAILABLE", self.reason)

    def close(self) -> None:
        return None


class PhoneLinkProvider:
    name = "phone-link"

    def __init__(self, bridge: PhoneLinkBridge | None = None) -> None:
        self.bridge = bridge or UnavailablePhoneLinkBridge()

    def list_devices(self) -> Sequence[DeviceState]:
        return self.bridge.list_devices()

    def get_state(self, device_id: str) -> DeviceResult:
        return self.bridge.state(device_id)

    def capabilities(self, device_id: str) -> frozenset[DeviceCapability]:
        state = next((d for d in self.list_devices() if d.device_id == device_id), None)
        if state is None or not state.connected:
            return frozenset()
        return frozenset({DeviceCapability.STATE_READ, DeviceCapability.SCREEN_VIEW, DeviceCapability.INPUT_CONTROL})

    def view_screen(self, device_id: str) -> DeviceResult:
        return self.bridge.screen(device_id)

    def send_input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult:
        return self.bridge.input(device_id, event)

    def read_notifications(self, device_id: str) -> DeviceResult:
        return self.bridge.notifications(device_id)

    def transfer_file(self, device_id: str, direction: FileTransferDirection, path: str) -> DeviceResult:
        return self.bridge.transfer(device_id, direction, path)

    def open_app(self, device_id: str, app_id: str) -> DeviceResult:
        return self.bridge.open_app(device_id, app_id)

    def close(self) -> None:
        self.bridge.close()
