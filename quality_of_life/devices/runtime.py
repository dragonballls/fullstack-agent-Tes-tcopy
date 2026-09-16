"""Runtime-facing physical device tool with safe provider discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from ..permissions import CapabilityPolicy
from .android_adb import AndroidAdbProvider
from .automation import DeviceAutomation
from .facade import DeviceFacade
from .models import DeviceResult
from .phone_link import PhoneLinkProvider
from .provider import DeviceInputEvent, FileTransferDirection
from .registry import DeviceRegistry


class DeviceTool:
    """Lazy physical-device service used by the Jarvis runtime.

    Direct ADB control is the primary real-device transport. Phone Link is
    registered as a capability-driven Windows transport boundary. Neither
    transport is mandatory for startup or CI.
    """

    def __init__(
        self,
        policy: CapabilityPolicy,
        confirmation: Callable[[str], bool] | None = None,
        providers: tuple[Any, ...] | None = None,
    ) -> None:
        self.policy = policy
        self.providers = providers or (AndroidAdbProvider(), PhoneLinkProvider())
        self.registry = DeviceRegistry(self.providers)
        self.facade = DeviceFacade(self.registry, policy, confirmation)
        self.automation = DeviceAutomation(self.facade, policy)
        self.registry.refresh()

    def refresh(self) -> DeviceResult:
        return self.registry.refresh()

    def list(self) -> tuple:
        return self.facade.list_devices()

    def state(self, device_id: str) -> DeviceResult:
        return self.facade.state(device_id)

    def select(self, device_id: str) -> DeviceResult:
        return self.facade.select(device_id)

    def active(self) -> DeviceResult:
        return self.registry.active()

    def screen(self, device_id: str) -> DeviceResult:
        return self.facade.screen(device_id)

    def input(
        self,
        device_id: str,
        kind: str,
        *,
        x: float | None = None,
        y: float | None = None,
        text: str | None = None,
        amount: float | None = None,
        confirmed: bool = False,
    ) -> DeviceResult:
        return self.facade.input(
            device_id,
            DeviceInputEvent(kind, x=x, y=y, text=text, amount=amount),
            confirmed=confirmed,
        )

    def notifications(self, device_id: str) -> DeviceResult:
        return self.facade.notifications(device_id)

    def transfer(
        self, device_id: str, direction: str, path: str, confirmed: bool = False
    ) -> DeviceResult:
        try:
            transfer_direction = FileTransferDirection(direction)
        except ValueError:
            return DeviceResult.failure("INVALID", f"Unknown transfer direction: {direction}")
        return self.facade.transfer(device_id, transfer_direction, path, confirmed=confirmed)

    def open_app(self, device_id: str, app_id: str, confirmed: bool = False) -> DeviceResult:
        return self.facade.open_app(device_id, app_id, confirmed=confirmed)

    def automate(
        self,
        device_id: str,
        steps: Iterable[Mapping[str, object]],
        confirmed: bool = False,
    ) -> DeviceResult:
        return self.automation.run_steps(device_id, steps, confirmed=confirmed)

    def close(self) -> None:
        for provider in self.providers:
            provider.close()
