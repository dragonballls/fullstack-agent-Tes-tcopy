"""Capability policy used by quality-of-life tools."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CapabilityDenied(PermissionError):
    """Raised when a tool operation is outside the configured capability set."""


class Capability(str, Enum):
    SCREEN_READ = "screen.read"
    LOCATION_READ = "location.read"
    LOCATION_WRITE = "location.write"
    MOUSE_CONTROL = "mouse.control"
    KEYBOARD_CONTROL = "keyboard.control"
    CLIPBOARD = "clipboard"
    WINDOW_CONTROL = "window.control"
    APP_LAUNCH = "app.launch"
    BROWSER_CONTROL = "browser.control"
    REPO_READ = "repo.read"
    REPO_WRITE = "repo.write"
    ACCOUNT_READ = "account.read"
    ACCOUNT_WRITE = "account.write"
    FILE_READ = "file.read"
    FILE_WRITE = "file.write"
    FILE_DELETE = "file.delete"
    APP_READ = "app.read"
    APP_WRITE = "app.write"
    PROCESS_READ = "process.read"
    PROCESS_CONTROL = "process.control"
    SERVICE_READ = "service.read"
    SERVICE_CONTROL = "service.control"
    SYSTEM_SETTINGS = "system.settings"
    BACKGROUND_JOBS = "background.jobs"
    CLOUD_ROUTING = "cloud.routing"
    SYSTEM_DIAGNOSTICS = "system.diagnostics"
    SYSTEM_MAINTENANCE = "system.maintenance"
    DEVICE_READ = "device.read"
    DEVICE_SCREEN = "device.screen"
    DEVICE_INPUT = "device.input"
    DEVICE_NOTIFICATIONS = "device.notifications"
    DEVICE_FILES = "device.files"
    DEVICE_APPS = "device.apps"
    DEVICE_AUTOMATION = "device.automation"


@dataclass(frozen=True)
class CapabilityPolicy:
    """Small deny-by-default policy shared by all quality-of-life tools."""

    allowed: frozenset[Capability] = frozenset()
    require_confirmation: frozenset[Capability] = frozenset({
        Capability.MOUSE_CONTROL,
        Capability.KEYBOARD_CONTROL,
        Capability.WINDOW_CONTROL,
        Capability.APP_LAUNCH,
        Capability.BROWSER_CONTROL,
        Capability.REPO_WRITE,
        Capability.ACCOUNT_WRITE,
        Capability.LOCATION_WRITE,
        Capability.FILE_WRITE,
        Capability.FILE_DELETE,
        Capability.APP_WRITE,
        Capability.PROCESS_CONTROL,
        Capability.SERVICE_CONTROL,
        Capability.SYSTEM_SETTINGS,
        Capability.BACKGROUND_JOBS,
        Capability.SYSTEM_MAINTENANCE,
        Capability.DEVICE_INPUT,
        Capability.DEVICE_FILES,
        Capability.DEVICE_APPS,
        Capability.DEVICE_AUTOMATION,
    })

    def check(self, capability: Capability) -> None:
        if capability not in self.allowed:
            raise CapabilityDenied(f"Capability is not enabled: {capability.value}")

    def needs_confirmation(self, capability: Capability) -> bool:
        return capability in self.require_confirmation
