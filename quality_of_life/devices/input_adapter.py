"""Translate Jarvis computer/hand input into device input events."""

from __future__ import annotations

from .facade import DeviceFacade
from .models import DeviceResult
from .provider import DeviceInputEvent


class DeviceInputAdapter:
    """Bridge existing hand/computer-control events into the active device."""

    def __init__(self, facade: DeviceFacade) -> None:
        self.facade = facade

    def route(self, target_device_id: str, kind: str, **payload: object) -> DeviceResult:
        event = DeviceInputEvent(
            kind=kind,
            x=float(payload["x"]) if payload.get("x") is not None else None,
            y=float(payload["y"]) if payload.get("y") is not None else None,
            text=str(payload["text"]) if payload.get("text") is not None else None,
            amount=float(payload["amount"]) if payload.get("amount") is not None else None,
        )
        return self.facade.input(target_device_id, event, confirmed=bool(payload.get("confirmed", False)))
