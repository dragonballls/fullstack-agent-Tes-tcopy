"""Provider interface for real devices.

Providers adapt operating-system/device-specific transports into stable Jarvis
operations. CI uses fake providers and never requires a live phone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from .models import DeviceCapability, DeviceResult, DeviceState


class FileTransferDirection(str, Enum):
    TO_DEVICE = "to_device"
    FROM_DEVICE = "from_device"


@dataclass(frozen=True)
class DeviceInputEvent:
    kind: str
    x: float | None = None
    y: float | None = None
    text: str | None = None
    amount: float | None = None

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("kind must not be empty")


class PhoneDeviceProvider(Protocol):
    """Adapter contract for a physical Android device transport."""

    name: str

    def list_devices(self) -> Sequence[DeviceState]: ...

    def get_state(self, device_id: str) -> DeviceResult: ...

    def capabilities(self, device_id: str) -> frozenset[DeviceCapability]: ...

    def view_screen(self, device_id: str) -> DeviceResult: ...

    def send_input(self, device_id: str, event: DeviceInputEvent) -> DeviceResult: ...

    def read_notifications(self, device_id: str) -> DeviceResult: ...

    def transfer_file(
        self, device_id: str, direction: FileTransferDirection, path: str
    ) -> DeviceResult: ...

    def open_app(self, device_id: str, app_id: str) -> DeviceResult: ...

    def close(self) -> None: ...
