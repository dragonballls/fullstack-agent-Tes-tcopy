"""Translate Jarvis computer/hand input into device input events."""

from __future__ import annotations

from .facade import DeviceFacade
from .models import DeviceResult
from .provider import DeviceInputEvent


class DeviceInputAdapter:
    """Bridge existing hand/computer-control events into a selected device."""

    def __init__(self, facade: DeviceFacade) -> None:
        self.facade = facade
        self._hand_points: dict[str, tuple[int, int]] = {}

    def route(self, target_device_id: str, kind: str, **payload: object) -> DeviceResult:
        event = DeviceInputEvent(
            kind=kind,
            x=float(payload["x"]) if payload.get("x") is not None else None,
            y=float(payload["y"]) if payload.get("y") is not None else None,
            text=str(payload["text"]) if payload.get("text") is not None else None,
            amount=float(payload["amount"]) if payload.get("amount") is not None else None,
        )
        return self.facade.input(target_device_id, event, confirmed=bool(payload.get("confirmed", False)))

    def route_hand_event(self, target_device_id: str, event: object, *, confirmed: bool = False) -> DeviceResult:
        """Track a normalized hand point; pinch-release becomes a real device tap."""
        kind = str(getattr(event, "kind", ""))
        if kind == "pause":
            self._hand_points.pop(target_device_id, None)
            return DeviceResult.success("hand control paused")
        provider = self.facade.registry.provider_for(target_device_id)
        if provider is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        if kind == "move":
            x = getattr(event, "x", None)
            y = getattr(event, "y", None)
            if x is None or y is None:
                return DeviceResult.failure("INVALID", "hand move requires coordinates")
            size = provider.display_size(target_device_id)
            if size is None:
                return DeviceResult.failure("UNAVAILABLE", "Device display dimensions are unavailable")
            width, height = size
            self._hand_points[target_device_id] = (
                round(float(x) * max(width - 1, 0)),
                round(float(y) * max(height - 1, 0)),
            )
            return DeviceResult.success("hand point tracked", x=self._hand_points[target_device_id][0], y=self._hand_points[target_device_id][1])
        if kind == "click":
            point = self._hand_points.get(target_device_id)
            if point is None:
                return DeviceResult.failure("NO_POINT", "No hand point is available for the selected device")
            return self.facade.input(
                target_device_id,
                DeviceInputEvent("tap", x=point[0], y=point[1]),
                confirmed=confirmed,
            )
        return DeviceResult.failure("UNSUPPORTED", f"Unsupported hand event: {kind}")
