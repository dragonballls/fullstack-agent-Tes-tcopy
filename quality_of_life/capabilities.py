"""Stable catalog of typed capabilities exposed by the agent."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .permissions import Capability


class OperationRisk(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"
    EXTERNAL = "external"


@dataclass(frozen=True)
class OperationSpec:
    name: str
    capability: Capability
    risk: OperationRisk
    description: str


OPERATION_CATALOG: tuple[OperationSpec, ...] = (
    OperationSpec("computer.move", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Move the pointer"),
    OperationSpec("computer.click", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Click at the current pointer position"),
    OperationSpec("computer.type_text", Capability.KEYBOARD_CONTROL, OperationRisk.EXTERNAL, "Type text into the focused application"),
    OperationSpec("computer.open_app", Capability.APP_LAUNCH, OperationRisk.EXTERNAL, "Launch a known application"),
    OperationSpec("hand_control.start", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Enable webcam-driven pointer control"),
    OperationSpec("hand_control.stop", Capability.MOUSE_CONTROL, OperationRisk.MUTATE, "Stop webcam-driven pointer control"),
    OperationSpec("screen.capture", Capability.SCREEN_READ, OperationRisk.READ, "Capture the current screen"),
    OperationSpec("browser.start", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Start a selected installed browser"),
    OperationSpec("browser.open_url", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Open a validated web URL"),
    OperationSpec("browser.navigate", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Navigate the controlled browser"),
    OperationSpec("browser.click", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Click a browser element"),
    OperationSpec("browser.fill", Capability.BROWSER_CONTROL, OperationRisk.EXTERNAL, "Fill a browser field"),
    OperationSpec("browser.read_text", Capability.BROWSER_CONTROL, OperationRisk.READ, "Read browser page text"),
    OperationSpec("browser.pages", Capability.BROWSER_CONTROL, OperationRisk.READ, "List controlled browser pages"),
    OperationSpec("files.search", Capability.FILE_READ, OperationRisk.READ, "Search within permitted filesystem locations"),
    OperationSpec("files.read", Capability.FILE_READ, OperationRisk.READ, "Read a text file"),
    OperationSpec("files.write", Capability.FILE_WRITE, OperationRisk.MUTATE, "Write a text file"),
    OperationSpec("files.copy", Capability.FILE_WRITE, OperationRisk.MUTATE, "Copy a file or directory"),
    OperationSpec("files.move", Capability.FILE_WRITE, OperationRisk.MUTATE, "Move a file or directory"),
    OperationSpec("files.delete", Capability.FILE_DELETE, OperationRisk.DESTRUCTIVE, "Delete an explicitly selected path"),
    OperationSpec("applications.list", Capability.APP_READ, OperationRisk.READ, "List installed applications"),
    OperationSpec("applications.install", Capability.APP_WRITE, OperationRisk.EXTERNAL, "Install a selected package through Windows package management"),
    OperationSpec("applications.update", Capability.APP_WRITE, OperationRisk.EXTERNAL, "Update a selected package through Windows package management"),
    OperationSpec("applications.uninstall", Capability.APP_WRITE, OperationRisk.DESTRUCTIVE, "Uninstall a uniquely selected application"),
    OperationSpec("processes.list", Capability.PROCESS_READ, OperationRisk.READ, "Inspect running processes"),
    OperationSpec("processes.stop", Capability.PROCESS_CONTROL, OperationRisk.MUTATE, "Stop a selected process"),
    OperationSpec("services.list", Capability.SERVICE_READ, OperationRisk.READ, "Inspect Windows services"),
    OperationSpec("services.restart", Capability.SERVICE_CONTROL, OperationRisk.MUTATE, "Restart a selected service"),
    OperationSpec("system.inspect", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Inspect supported system state"),
    OperationSpec("system.change_setting", Capability.SYSTEM_SETTINGS, OperationRisk.MUTATE, "Change a supported setting"),
    OperationSpec("background.start", Capability.BACKGROUND_JOBS, OperationRisk.MUTATE, "Start a bounded background job"),
    OperationSpec("background.cancel", Capability.BACKGROUND_JOBS, OperationRisk.MUTATE, "Cancel a background job"),
    OperationSpec("accounts.list", Capability.ACCOUNT_READ, OperationRisk.READ, "List explicitly configured external account grants"),
    OperationSpec("accounts.connect", Capability.ACCOUNT_WRITE, OperationRisk.EXTERNAL, "Start an explicit OAuth connection flow"),
    OperationSpec("accounts.select", Capability.ACCOUNT_READ, OperationRisk.READ, "Select one already-authorized account identity"),
    OperationSpec("accounts.service_action", Capability.ACCOUNT_WRITE, OperationRisk.EXTERNAL, "Run an explicitly authorized external account service action"),
    OperationSpec("accounts.github_fork", Capability.ACCOUNT_WRITE, OperationRisk.EXTERNAL, "Create a GitHub fork through an authorized account"),
    OperationSpec("locations.current", Capability.LOCATION_READ, OperationRisk.READ, "Determine the current location through an approved provider"),
    OperationSpec("locations.save", Capability.LOCATION_WRITE, OperationRisk.MUTATE, "Save a user-named location"),
    OperationSpec("locations.save_current", Capability.LOCATION_WRITE, OperationRisk.MUTATE, "Save the current approved location under a user-provided name"),
    OperationSpec("locations.get", Capability.LOCATION_READ, OperationRisk.READ, "Retrieve a saved named location"),
    OperationSpec("locations.list", Capability.LOCATION_READ, OperationRisk.READ, "List saved named locations"),
    OperationSpec("locations.delete", Capability.LOCATION_WRITE, OperationRisk.DESTRUCTIVE, "Delete a saved named location"),
    OperationSpec("self_coding.run", Capability.REPO_WRITE, OperationRisk.EXTERNAL, "Run guarded repository coding"),
    OperationSpec("windows_maintenance.diagnose", Capability.SYSTEM_DIAGNOSTICS, OperationRisk.READ, "Diagnose Windows state"),
    OperationSpec("windows_maintenance.handle", Capability.SYSTEM_MAINTENANCE, OperationRisk.DESTRUCTIVE, "Perform a guarded Windows maintenance action"),
    OperationSpec("devices.list", Capability.DEVICE_READ, OperationRisk.READ, "List authorized physical devices"),
    OperationSpec("devices.refresh", Capability.DEVICE_READ, OperationRisk.READ, "Refresh physical device discovery"),
    OperationSpec("devices.state", Capability.DEVICE_READ, OperationRisk.READ, "Read selected device state"),
    OperationSpec("devices.select", Capability.DEVICE_READ, OperationRisk.MUTATE, "Select the active physical device"),
    OperationSpec("devices.active", Capability.DEVICE_READ, OperationRisk.READ, "Read the active physical device"),
    OperationSpec("devices.screen", Capability.DEVICE_SCREEN, OperationRisk.READ, "View the actual device screen when supported"),
    OperationSpec("devices.input", Capability.DEVICE_INPUT, OperationRisk.MUTATE, "Send an input event to a physical device"),
    OperationSpec("devices.notifications", Capability.DEVICE_NOTIFICATIONS, OperationRisk.READ, "Read supported device notifications"),
    OperationSpec("devices.files", Capability.DEVICE_FILES, OperationRisk.EXTERNAL, "Transfer a file with a physical device"),
    OperationSpec("devices.apps", Capability.DEVICE_APPS, OperationRisk.EXTERNAL, "Open a supported application on a physical device"),
    OperationSpec("devices.automate", Capability.DEVICE_AUTOMATION, OperationRisk.EXTERNAL, "Run a guarded automation against a physical device"),
)


def operation(name: str) -> OperationSpec:
    for spec in OPERATION_CATALOG:
        if spec.name == name:
            return spec
    raise KeyError(f"unknown capability operation: {name}")


def operations_for(capability: Capability) -> tuple[OperationSpec, ...]:
    return tuple(spec for spec in OPERATION_CATALOG if spec.capability is capability)
