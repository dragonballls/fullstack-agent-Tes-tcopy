"""Environment diagnostics for real-device transports."""

from __future__ import annotations

from dataclasses import dataclass
import shutil


@dataclass(frozen=True)
class TransportReadiness:
    name: str
    available: bool
    detail: str


@dataclass(frozen=True)
class DeviceReadiness:
    adb: TransportReadiness
    scrcpy: TransportReadiness
    phone_link: TransportReadiness

    @property
    def ready_for_direct_android(self) -> bool:
        return self.adb.available

    @property
    def ready_for_live_screen(self) -> bool:
        return self.adb.available and self.scrcpy.available


def check_readiness() -> DeviceReadiness:
    adb = shutil.which("adb")
    scrcpy = shutil.which("scrcpy")
    return DeviceReadiness(
        TransportReadiness("android-adb", bool(adb), f"adb: {adb}" if adb else "adb not found on PATH"),
        TransportReadiness("scrcpy", bool(scrcpy), f"scrcpy: {scrcpy}" if scrcpy else "scrcpy not found on PATH"),
        TransportReadiness("phone-link", False, "Phone Link bridge not configured"),
    )
