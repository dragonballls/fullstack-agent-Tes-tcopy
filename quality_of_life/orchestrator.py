"""Capability-aware dispatcher joining the quality-of-life tools together."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .permissions import Capability, CapabilityPolicy


@dataclass(frozen=True)
class Action:
    capability: Capability
    operation: str
    execute: Callable[..., Any]


ConfirmationHook = Callable[[Capability, str], bool]


class QoLOrchestrator:
    """Dispatch registered actions only after capability and confirmation checks."""

    def __init__(self, policy: CapabilityPolicy) -> None:
        self.policy = policy
        self._actions: dict[tuple[Capability, str], Action] = {}
        self._device_tool: Any | None = None

    def register(self, action: Action) -> None:
        key = (action.capability, action.operation)
        if key in self._actions:
            raise ValueError(f"action already registered: {action.capability.value}/{action.operation}")
        self._actions[key] = action

    def _device_action(self, operation: str, confirmation: ConfirmationHook | None) -> Callable[..., Any] | None:
        if not operation.startswith("devices."):
            return None
        if self._device_tool is None:
            from .devices.runtime import DeviceTool
            device_confirmation = None
            if confirmation is not None:
                device_confirmation = lambda op: confirmation(self.policy_operation_capability(operation), op)
            self._device_tool = DeviceTool(self.policy, confirmation=device_confirmation)
        actions: dict[str, Callable[..., Any]] = {
            "devices.list": self._device_tool.list,
            "devices.refresh": self._device_tool.refresh,
            "devices.state": self._device_tool.state,
            "devices.select": self._device_tool.select,
            "devices.active": self._device_tool.active,
            "devices.screen": self._device_tool.screen,
            "devices.input": self._device_tool.input,
            "devices.notifications": self._device_tool.notifications,
            "devices.files": self._device_tool.transfer,
            "devices.apps": self._device_tool.open_app,
            "devices.automate": self._device_tool.automate,
        }
        return actions.get(operation)

    @staticmethod
    def policy_operation_capability(operation: str) -> Capability:
        return {
            "devices.list": Capability.DEVICE_READ,
            "devices.refresh": Capability.DEVICE_READ,
            "devices.state": Capability.DEVICE_READ,
            "devices.select": Capability.DEVICE_READ,
            "devices.active": Capability.DEVICE_READ,
            "devices.screen": Capability.DEVICE_SCREEN,
            "devices.input": Capability.DEVICE_INPUT,
            "devices.notifications": Capability.DEVICE_NOTIFICATIONS,
            "devices.files": Capability.DEVICE_FILES,
            "devices.apps": Capability.DEVICE_APPS,
            "devices.automate": Capability.DEVICE_AUTOMATION,
        }.get(operation, Capability.DEVICE_READ)

    def run(
        self,
        capability: Capability,
        operation: str,
        *args: Any,
        confirmation: ConfirmationHook | None = None,
        **kwargs: Any,
    ) -> Any:
        self.policy.check(capability)
        if self.policy.needs_confirmation(capability):
            if confirmation is None:
                raise PermissionError(f"Confirmation is required: {capability.value}/{operation}")
            if not confirmation(capability, operation):
                raise PermissionError(f"Confirmation was denied: {capability.value}/{operation}")
        try:
            action = self._actions[(capability, operation)]
        except KeyError:
            action = None
        if action is None:
            action = self._device_action(operation, confirmation)
        if action is None:
            raise KeyError(f"action not registered: {capability.value}/{operation}")
        if isinstance(action, Action):
            return action.execute(*args, **kwargs)
        return action(*args, **kwargs)
