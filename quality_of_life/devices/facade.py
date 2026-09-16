"""Capability-checked facade over physical-device providers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..permissions import Capability, CapabilityDenied, CapabilityPolicy
from .models import DeviceResult
from .provider import DeviceInputEvent, FileTransferDirection
from .registry import DeviceRegistry


ConfirmationHook = Callable[[str], bool]


class DeviceFacade:
    def __init__(
        self,
        registry: DeviceRegistry,
        policy: CapabilityPolicy,
        confirmation: ConfirmationHook | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy
        self.confirmation = confirmation

    def _provider(self, device_id: str):
        provider = self.registry.provider_for(device_id)
        if provider is None:
            raise KeyError("device is not registered")
        return provider

    def _check(self, capability: Capability, operation: str, confirmed: bool = False) -> None:
        self.policy.check(capability)
        if self.policy.needs_confirmation(capability) and not confirmed:
            if self.confirmation is None or not self.confirmation(operation):
                raise CapabilityDenied(f"Confirmation required: {operation}")

    def list_devices(self) -> tuple:
        return self.registry.list()

    def state(self, device_id: str) -> DeviceResult:
        self.policy.check(Capability.DEVICE_READ)
        return self._provider(device_id).get_state(device_id)

    def select(self, device_id: str) -> DeviceResult:
        self.policy.check(Capability.DEVICE_READ)
        return self.registry.select(device_id)

    def screen(self, device_id: str) -> DeviceResult:
        self._check(Capability.DEVICE_SCREEN, "devices.screen")
        return self._provider(device_id).view_screen(device_id)

    def screen_all(self) -> tuple[DeviceResult, ...]:
        """Open a live mirror for every currently connected registered device."""
        self.policy.check(Capability.DEVICE_SCREEN)
        results: list[DeviceResult] = []
        for device in self.registry.list():
            if not device.connected:
                continue
            try:
                results.append(self._provider(device.device_id).view_screen(device.device_id))
            except Exception as exc:
                results.append(DeviceResult.failure("DEVICE_ERROR", f"Unable to open {device.label}: {exc}"))
        return tuple(results)

    def input(self, device_id: str, event: DeviceInputEvent, confirmed: bool = False) -> DeviceResult:
        self._check(Capability.DEVICE_INPUT, "devices.input", confirmed)
        return self._provider(device_id).send_input(device_id, event)

    def notifications(self, device_id: str) -> DeviceResult:
        self.policy.check(Capability.DEVICE_NOTIFICATIONS)
        return self._provider(device_id).read_notifications(device_id)

    def transfer(
        self,
        device_id: str,
        direction: FileTransferDirection,
        path: str,
        confirmed: bool = False,
    ) -> DeviceResult:
        if not path.strip():
            return DeviceResult.failure("INVALID", "path must not be empty")
        self._check(Capability.DEVICE_FILES, "devices.files", confirmed)
        return self._provider(device_id).transfer_file(device_id, direction, path)

    def open_app(self, device_id: str, app_id: str, confirmed: bool = False) -> DeviceResult:
        if not app_id.strip():
            return DeviceResult.failure("INVALID", "app_id must not be empty")
        self._check(Capability.DEVICE_APPS, "devices.apps", confirmed)
        return self._provider(device_id).open_app(device_id, app_id)
