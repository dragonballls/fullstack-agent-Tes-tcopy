"""Lazy capability registry for the quality-of-life layer."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    factory: str

    def resolve(self) -> Any:
        module_name, attribute = self.factory.rsplit(".", 1)
        return getattr(importlib.import_module(module_name), attribute)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool already registered: {spec.name}")
        self._tools[spec.name] = spec

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown quality-of-life tool: {name}") from exc


def default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec("account_access", "Explicit user-authorized external accounts and scoped credentials", "quality_of_life.account_access.AccountAccessRegistry"))
    registry.register(ToolSpec("account_manager", "Multi-account connection, selection, OAuth handoff, and guarded service actions", "quality_of_life.account_manager.AccountServiceManager"))
    registry.register(ToolSpec("account_integrations", "Secret-safe account identities and OAuth contracts", "quality_of_life.account_integrations.AccountIdentity"))
    registry.register(ToolSpec("service_adapters", "Guarded Google, Microsoft, YouTube, GitHub, and browser service adapters", "quality_of_life.service_adapters.ApiServiceAdapter"))
    registry.register(ToolSpec("applications", "Installed application inventory and confirmed uninstall", "quality_of_life.applications.ApplicationManager"))
    registry.register(ToolSpec("background", "Bounded cancellable background jobs", "quality_of_life.background.BackgroundJobs"))
    registry.register(ToolSpec("browser", "Optional Playwright browser automation", "quality_of_life.browser.BrowserController"))
    registry.register(ToolSpec("browser_registry", "Installed desktop browser discovery and selection", "quality_of_life.browser_registry.BrowserRegistry"))
    registry.register(ToolSpec("clipboard", "Bounded clipboard text read/write", "quality_of_life.clipboard.ClipboardController"))
    registry.register(ToolSpec("cloud_router", "Ordered cloud-provider failover", "quality_of_life.router.CloudModelRouter"))
    registry.register(ToolSpec("computer", "Windows mouse, keyboard, scrolling, and app launch", "quality_of_life.computer.ComputerController"))
    registry.register(ToolSpec("devices", "Real Android devices through authorized device providers; supports multi-device state, screen, input, apps, and files", "quality_of_life.devices.runtime.DeviceTool"))
    registry.register(ToolSpec("hand_control", "Optional webcam hand tracking bridged to guarded computer input", "quality_of_life.hand_control.HandControlBridge"))
    registry.register(ToolSpec("hand_control_runtime", "Isolated lifecycle manager for optional webcam hand control", "quality_of_life.hand_control_runtime.HandControlRuntime"))
    registry.register(ToolSpec("hand_control_server", "Loopback-only webcam hand-control bridge", "quality_of_life.hand_control_server.HandControlHandler"))
    registry.register(ToolSpec("voice_listener", "Local always-listening wake-word microphone listener", "quality_of_life.voice_listener.LocalWakeWordListener"))
    registry.register(ToolSpec("files", "Guarded filesystem read and mutation operations", "quality_of_life.files.FileController"))
    registry.register(ToolSpec("gods_eye", "Location search, current-location context, routing, and in-app map state", "quality_of_life.gods_eye.GodsEye"))
    registry.register(ToolSpec("locations", "Persistent user-named locations backed by a local JSON store", "quality_of_life.location_memory.SavedLocationStore"))
    registry.register(ToolSpec("processes", "Guarded process and service inspection", "quality_of_life.processes.ProcessManager"))
    registry.register(ToolSpec("scheduler", "Bounded delayed background jobs", "quality_of_life.scheduler.Scheduler"))
    registry.register(ToolSpec("screen", "Screen capture for computer-aware reasoning", "quality_of_life.screen.ScreenCapture"))
    registry.register(ToolSpec("self_coding", "Guarded autonomous repository coding with verification and rollback", "self_coding.agent.SelfCodingAgent"))
    registry.register(ToolSpec("system", "Structured system inspection and allowlisted settings", "quality_of_life.system.SystemController"))
    registry.register(ToolSpec("windows", "Windows window enumeration and management", "quality_of_life.windows.WindowsController"))
    registry.register(ToolSpec("windows_maintenance", "Guarded Windows PC diagnostics, background-process cleanup, startup management, and confirmed repairs", "windows_maintenance.facade.MaintenanceFacade"))
    return registry
