"""Domain models for real connected devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class DeviceCapability(str, Enum):
    STATE_READ = "state.read"
    SCREEN_VIEW = "screen.view"
    INPUT_CONTROL = "input.control"
    NOTIFICATION_READ = "notifications.read"
    CALLS = "calls"
    MESSAGES = "messages"
    FILES = "files"
    APP_CONTROL = "apps.control"
    AUTOMATION = "automation"


@dataclass(frozen=True)
class DeviceState:
    device_id: str
    label: str
    connected: bool
    battery_percent: int | None = None
    charging: bool | None = None
    provider: str | None = None

    def __post_init__(self) -> None:
        if not self.device_id.strip():
            raise ValueError("device_id must not be empty")
        if not self.label.strip():
            raise ValueError("label must not be empty")
        if self.battery_percent is not None and not 0 <= self.battery_percent <= 100:
            raise ValueError("battery_percent must be between 0 and 100")


@dataclass(frozen=True)
class DeviceResult:
    ok: bool
    code: str
    message: str
    data: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def success(cls, message: str = "ok", **data: Any) -> "DeviceResult":
        return cls(True, "OK", message, data)

    @classmethod
    def failure(cls, code: str, message: str, **data: Any) -> "DeviceResult":
        return cls(False, code, message, data)
