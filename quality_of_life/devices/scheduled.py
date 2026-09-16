"""Adapter from the existing scheduler to physical-device automations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime

from ..scheduler import Scheduler, ScheduledJob
from .automation import DeviceAutomation
from .facade import DeviceFacade
from .models import DeviceResult


class ScheduledDeviceAutomation:
    def __init__(self, facade: DeviceFacade, scheduler: Scheduler) -> None:
        self.facade = facade
        self.scheduler = scheduler
        self.automation = DeviceAutomation(facade, facade.policy)

    def schedule_once(
        self,
        name: str,
        run_at: datetime,
        device_id: str,
        steps: Iterable[Mapping[str, object]],
        confirmed: bool = False,
    ) -> ScheduledJob:
        normalized = tuple(dict(step) for step in steps)
        if not normalized:
            raise ValueError("automation requires at least one step")

        def run(cancel):
            result = self.automation.run_steps(device_id, normalized, cancel=cancel, confirmed=confirmed)
            if not result.ok:
                raise RuntimeError(f"device automation failed: {result.code}: {result.message}")

        return self.scheduler.schedule_once(name, run_at, run)
