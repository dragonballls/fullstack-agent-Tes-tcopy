"""Registry and active-device context for physical devices."""

from __future__ import annotations

from typing import Iterable

from .models import DeviceResult, DeviceState
from .provider import PhoneDeviceProvider


class DeviceRegistry:
    def __init__(self, providers: Iterable[PhoneDeviceProvider] = ()) -> None:
        self._providers: list[PhoneDeviceProvider] = list(providers)
        self._devices: dict[str, tuple[PhoneDeviceProvider, DeviceState]] = {}
        self._active_id: str | None = None

    def register_provider(self, provider: PhoneDeviceProvider) -> None:
        if provider not in self._providers:
            self._providers.append(provider)

    def refresh(self) -> DeviceResult:
        discovered: dict[str, tuple[PhoneDeviceProvider, DeviceState]] = {}
        errors: list[str] = []
        for provider in self._providers:
            try:
                states = provider.list_devices()
            except Exception as exc:
                errors.append(f"{getattr(provider, 'name', type(provider).__name__)}: {exc}")
                for device_id, (known_provider, known_state) in self._devices.items():
                    if known_provider is provider:
                        discovered[device_id] = (provider, known_state)
                continue
            for state in states:
                existing = discovered.get(state.device_id)
                if existing is not None and existing[0] is not provider:
                    return DeviceResult.failure(
                        "DUPLICATE_ID",
                        f"Device ID is exposed by multiple providers: {state.device_id}",
                    )
                discovered[state.device_id] = (provider, state)
        self._devices = discovered
        if self._active_id not in self._devices:
            self._active_id = next(iter(self._devices), None)
        if errors:
            return DeviceResult.success(
                "device registry refreshed with provider errors",
                count=len(self._devices),
                errors=tuple(errors),
            )
        return DeviceResult.success("device registry refreshed", count=len(self._devices))

    def list(self) -> tuple[DeviceState, ...]:
        return tuple(state for _, state in self._devices.values())

    def get(self, device_id: str) -> DeviceResult:
        item = self._devices.get(device_id)
        if item is None:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        provider, state = item
        return DeviceResult.success("device found", state=state, provider=provider.name)

    def provider_for(self, device_id: str) -> PhoneDeviceProvider | None:
        item = self._devices.get(device_id)
        return item[0] if item else None

    def select(self, device_id: str) -> DeviceResult:
        if device_id not in self._devices:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        self._active_id = device_id
        return DeviceResult.success("active device selected", device_id=device_id)

    def active(self) -> DeviceResult:
        if self._active_id is None:
            return DeviceResult.failure("NO_ACTIVE_DEVICE", "No active device is selected")
        return self.get(self._active_id)

    def remove(self, device_id: str) -> DeviceResult:
        if device_id not in self._devices:
            return DeviceResult.failure("NOT_FOUND", "Device is not registered")
        self._devices.pop(device_id)
        if self._active_id == device_id:
            self._active_id = next(iter(self._devices), None)
        return DeviceResult.success("device removed", device_id=device_id)
