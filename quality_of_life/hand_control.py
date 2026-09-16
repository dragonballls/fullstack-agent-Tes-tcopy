"""Optional webcam hand-control bridge for Jarvis desktop or device input.

The browser-facing tracker only produces normalized gesture events. This
module owns the safety policy and translates those events into either the
existing ComputerController interface or a provider-neutral physical-device
input adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any


@dataclass(frozen=True)
class HandSample:
    x: float
    y: float
    pinch: bool
    fingers: int
    confidence: float


@dataclass(frozen=True)
class HandEvent:
    kind: str
    x: float | None = None
    y: float | None = None
    button: str = "left"
    amount: int = 0


class HandGestureInterpreter:
    """Convert stable hand poses into low-frequency, normalized input events."""

    def __init__(self, *, min_confidence: float = 0.80, click_cooldown_s: float = 0.35, move_deadzone: float = 0.003) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if click_cooldown_s < 0:
            raise ValueError("click_cooldown_s cannot be negative")
        if move_deadzone < 0:
            raise ValueError("move_deadzone cannot be negative")
        self.min_confidence = min_confidence
        self.click_cooldown_s = click_cooldown_s
        self.move_deadzone = move_deadzone
        self._previous: HandSample | None = None
        self._last_click = float("-inf")
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
        self._previous = None

    def enable(self) -> None:
        self._enabled = True
        self._previous = None

    @staticmethod
    def _valid(sample: HandSample) -> bool:
        return 0.0 <= sample.x <= 1.0 and 0.0 <= sample.y <= 1.0 and 0 <= sample.fingers <= 5 and math.isfinite(sample.confidence)

    def interpret(self, sample: HandSample, *, timestamp: float | None = None) -> tuple[HandEvent, ...]:
        now = time.monotonic() if timestamp is None else timestamp
        previous = self._previous
        self._previous = sample
        if not self._enabled or not self._valid(sample) or sample.confidence < self.min_confidence:
            return ()
        if sample.fingers == 0:
            self.disable()
            return (HandEvent(kind="pause"),)
        events: list[HandEvent] = []
        if sample.fingers == 1:
            moved = previous is None or abs(sample.x - previous.x) >= self.move_deadzone or abs(sample.y - previous.y) >= self.move_deadzone
            if moved:
                events.append(HandEvent(kind="move", x=sample.x, y=sample.y))
        if previous is not None and previous.pinch and not sample.pinch and now - self._last_click >= self.click_cooldown_s:
            self._last_click = now
            events.append(HandEvent(kind="click"))
        return tuple(events)


class HandControlBridge:
    """Guarded adapter from HandEvents to desktop or physical-device input."""

    def __init__(self, *, enabled: bool = False, controller: Any | None = None, device_adapter: Any | None = None, target_device_id: str | None = None) -> None:
        self.enabled = enabled
        self.controller = controller
        self.device_adapter = device_adapter
        self.target_device_id = target_device_id

    def set_device_target(self, device_id: str | None) -> None:
        self.target_device_id = device_id

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False
        if self.controller is not None and hasattr(self.controller, "pyautogui"):
            try:
                self.controller.pyautogui.mouseUp()
            except Exception:
                pass

    @staticmethod
    def _screen_coordinates(x: float, y: float, width: int, height: int) -> tuple[int, int]:
        if not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
            raise ValueError("hand coordinates must be normalized to 0..1")
        return round(x * max(width - 1, 0)), round(y * max(height - 1, 0))

    def dispatch(self, event: HandEvent) -> bool:
        if not self.enabled:
            return False
        if event.kind == "pause":
            self.disable()
            return True
        if self.target_device_id is not None:
            if self.device_adapter is None:
                return False
            result = self.device_adapter.route_hand_event(self.target_device_id, event, confirmed=True)
            return bool(getattr(result, "ok", False))
        if self.controller is None:
            return False
        if event.kind == "move":
            width, height = self.controller.pyautogui.size()
            x, y = self._screen_coordinates(float(event.x), float(event.y), int(width), int(height))
            self.controller.move(x, y)
            return True
        if event.kind == "click":
            self.controller.click(button=event.button)
            return True
        if event.kind == "scroll":
            self.controller.scroll(event.amount)
            return True
        return False
