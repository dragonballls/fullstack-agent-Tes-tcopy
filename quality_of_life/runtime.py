"""Unified capability-aware runtime for Jarvis quality-of-life tools."""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from .background import BackgroundJobs
from .gods_eye import GodsEye, Place
from .gods_eye_launcher import GodsEyeLauncher
from .intents import Intent, parse_intent
from .location import FallbackLocationProvider, IpLocationProvider, NominatimGeocoder, SystemLocationProvider
from .location_memory import SavedLocationStore
from .manifest import default_registry
from .orchestrator import Action, ConfirmationHook, QoLOrchestrator
from .permissions import Capability, CapabilityPolicy
from .router import CloudModelRouter, ProviderTarget
from .account_access import AccountAccessRegistry
from .account_integrations import ServiceProvider


class JarvisRuntime:
    """Lazy tool host that keeps capability and confirmation checks centralized."""

    def __init__(self, policy: CapabilityPolicy, confirmation: ConfirmationHook | None = None, factories: dict[str, Callable[[], Any]] | None = None, gods_eye_launcher: GodsEyeLauncher | None = None) -> None:
        self.policy = policy
        self.confirmation = confirmation
        self.registry = default_registry()
        self._factories = dict(factories or {})
        self._instances: dict[str, Any] = {}
        self.gods_eye_launcher = gods_eye_launcher or GodsEyeLauncher()
        self.orchestrator = QoLOrchestrator(policy)
        self._agent_orchestrator: Any | None = None
        self._health_monitor: Any | None = None
        self._register_actions()

    def available_tools(self) -> tuple[str, ...]:
        return self.registry.names()

    def _factory_from_spec(self, name: str) -> Callable[[], Any]:
        if name in self._factories:
            return self._factories[name]
        spec = self.registry.get(name)
        target = spec.resolve()
        if name == "account_access":
            return lambda: target.from_environment()
        if name == "account_manager":
            return lambda: target(account_access=self._tool("account_access"))
        if name in {"computer", "screen", "browser", "clipboard", "windows"}:
            return lambda: target(self.policy)
        if name == "browser_registry":
            return lambda: target()
        if name in {"files", "applications", "processes", "system"}:
            return lambda: target(self.policy)
        if name == "devices":
            def device_confirmation(operation: str) -> bool:
                if self.confirmation is None:
                    return False
                capability = QoLOrchestrator.policy_operation_capability(operation)
                return self.confirmation(capability, operation)
            return lambda: target(self.policy, confirmation=device_confirmation)
        if name == "scheduler":
            return lambda: target(self._tool("background"))
        if name == "gods_eye":
            return lambda: GodsEye(NominatimGeocoder(), FallbackLocationProvider(SystemLocationProvider(), IpLocationProvider()))
        if name == "locations":
            configured = os.environ.get("JARVIS_LOCATION_STORE")
            return lambda: SavedLocationStore(configured)
        if name == "hand_control_runtime":
            return lambda: target()
        if name == "hand_control":
            return lambda: target(
                enabled=False,
                controller=self._tool("computer"),
                device_adapter=self._tool("devices").input_adapter,
            )
        if name == "hand_control_server":
            return lambda: target
        if name == "background":
            return lambda: BackgroundJobs()
        if name == "cloud_router":
            explicit_base_url = os.environ.get("JARVIS_CLOUD_BASE_URL")
            if explicit_base_url:
                key_env = os.environ.get("JARVIS_CLOUD_API_KEY_ENV", "OPENAI_API_KEY")
                model = os.environ.get("JARVIS_CLOUD_MODEL")
                if not model:
                    raise RuntimeError("cloud router is not configured; set JARVIS_CLOUD_MODEL")
                target_config = ProviderTarget("primary", explicit_base_url, key_env, model)
            elif os.environ.get("JARVIS_OMNIROUTE_ENABLED", "1").strip().lower() not in {"0", "false", "no", "off"}:
                target_config = CloudModelRouter.omniroute_target()
            else:
                raise RuntimeError("cloud router is not configured; enable OmniRoute or set JARVIS_CLOUD_BASE_URL and JARVIS_CLOUD_MODEL")
            return lambda: CloudModelRouter((target_config,))
        if name == "self_coding":
            from self_coding import SelfCodingAgent, SelfCodingConfig
            configured_repo = os.environ.get("JARVIS_SELF_CODING_REPO")
            if not configured_repo:
                raise RuntimeError("self-coding is not configured; set JARVIS_SELF_CODING_REPO")
            return lambda: SelfCodingAgent(SelfCodingConfig(repo=Path(configured_repo), push_branch=os.environ.get("JARVIS_SELF_CODING_PUSH", "0").strip().lower() in {"1", "true", "yes", "on"}), max_passes=max(1, int(os.environ.get("JARVIS_SELF_CODING_MAX_PASSES", "1"))), backend=os.environ.get("JARVIS_SELF_CODING_BACKEND", "auto"))
        if name == "windows_maintenance":
            from windows_maintenance import MaintenanceFacade
            return lambda: MaintenanceFacade()
        raise RuntimeError(f"No runtime factory is configured for: {name}")

    def _tool(self, name: str) -> Any:
        if name not in self._instances:
            self._instances[name] = self._factory_from_spec(name)()
        return self._instances[name]

    def _assistant_orchestrator(self) -> Any:
        if self._agent_orchestrator is None:
            from .agent_orchestrator import AgentOrchestrator
            self._agent_orchestrator = AgentOrchestrator(self._tool("cloud_router"), self)
        return self._agent_orchestrator

    def _maintenance_facade(self) -> Any:
        return self._tool("windows_maintenance")

    def health_monitor(self) -> Any:
        if self._health_monitor is None:
            from .health_monitor import HealthMonitor
            self._health_monitor = HealthMonitor.from_environment(self._maintenance_facade())
        return self._health_monitor

    def start_health_monitor(self) -> bool:
        return self.health_monitor().start()

    def stop_health_monitor(self) -> None:
        if self._health_monitor is not None:
            self._health_monitor.stop()

    def health_snapshot(self) -> dict[str, Any]:
        return self.health_monitor().snapshot()

    def _register_actions(self) -> None:
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.move", lambda x, y: self._tool("computer").move(x, y)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.click", lambda button="left", clicks=1: self._tool("computer").click(button, clicks)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "computer.scroll", lambda amount: self._tool("computer").scroll(amount)))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.start", self._start_hand_control))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.stop", self._stop_hand_control))
        self.orchestrator.register(Action(Capability.MOUSE_CONTROL, "hand_control.status", lambda: self._tool("hand_control_runtime").status()))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.type_text", lambda text: self._tool("computer").type_text(text)))
        self.orchestrator.register(Action(Capability.KEYBOARD_CONTROL, "computer.hotkey", lambda *keys: self._tool("computer").hotkey(*keys)))
        self.orchestrator.register(Action(Capability.APP_LAUNCH, "computer.open_app", lambda command, *args: self._tool("computer").open_app(command, *args)))
        self.orchestrator.register(Action(Capability.SCREEN_READ, "screen.capture", lambda output=None: self._tool("screen").capture(output)))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.read", lambda: self._tool("clipboard").read()))
        self.orchestrator.register(Action(Capability.CLIPBOARD, "clipboard.write", lambda text: self._tool("clipboard").write(text)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.list", lambda: self._tool("windows").list_windows()))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.focus", lambda identifier: self._tool("windows").focus_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.minimize", lambda identifier: self._tool("windows").minimize_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.maximize", lambda identifier: self._tool("windows").maximize_window(identifier)))
        self.orchestrator.register(Action(Capability.WINDOW_CONTROL, "windows.close", lambda identifier: self._tool("windows").close_window(identifier)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.start", lambda browser=None: self._tool("browser").start(browser)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.open_url", lambda url, browser=None: self._tool("browser").open_url(url, browser=browser)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.navigate", lambda url: self._tool("browser").navigate(url)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.click", lambda selector: self._tool("browser").click(selector)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.fill", lambda selector, text: self._tool("browser").fill(selector, text)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.read_text", lambda selector="body": self._tool("browser").read_text(selector)))
        self.orchestrator.register(Action(Capability.BROWSER_CONTROL, "browser.pages", lambda: self._tool("browser").pages()))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.info", lambda path: self._tool("files").info(path)))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.search", lambda pattern, root=None, limit=100: self._tool("files").search(pattern, root, limit)))
        self.orchestrator.register(Action(Capability.FILE_READ, "files.read", lambda path, max_bytes=5_000_000: self._tool("files").read_text(path, max_bytes)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.write", lambda path, text: self._tool("files").write_text(path, text)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.copy", lambda source, destination: self._tool("files").copy(source, destination)))
        self.orchestrator.register(Action(Capability.FILE_WRITE, "files.move", lambda source, destination: self._tool("files").move(source, destination)))
        self.orchestrator.register(Action(Capability.FILE_DELETE, "files.delete", lambda path: self._tool("files").delete(path)))
        self.orchestrator.register(Action(Capability.APP_READ, "applications.list", lambda: self._tool("applications").list()))
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.install", lambda package_id, confirmed=False: self._tool("applications").install(package_id, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.update", lambda package_id, confirmed=False: self._tool("applications").update(package_id, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.APP_WRITE, "applications.uninstall", lambda name, confirmed=False: self._tool("applications").uninstall(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.PROCESS_READ, "processes.list", lambda: self._tool("processes").list_processes()))
        self.orchestrator.register(Action(Capability.PROCESS_CONTROL, "processes.stop", lambda pid, confirmed=False: self._tool("processes").stop(pid, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SERVICE_READ, "services.list", lambda: self._tool("processes").list_services()))
        self.orchestrator.register(Action(Capability.SERVICE_CONTROL, "services.restart", lambda name, confirmed=False: self._tool("processes").restart_service(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.inspect", lambda: self._tool("system").inspect()))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.network", lambda: self._tool("system").network()))
        self.orchestrator.register(Action(Capability.SYSTEM_DIAGNOSTICS, "system.get_setting", lambda name: self._tool("system").get_setting(name)))
        self.orchestrator.register(Action(Capability.SYSTEM_SETTINGS, "system.change_setting", lambda name, value, confirmed=False: self._tool("system").set_setting(name, value, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.start", lambda name, task: self._tool("background").start(name, task)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.cancel", lambda name: self._tool("background").cancel(name)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "background.active", lambda: self._tool("background").active()))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.schedule_once", lambda name, run_at, task: self._tool("scheduler").schedule_once(name, run_at, task)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.cancel", lambda name: self._tool("scheduler").cancel(name)))
        self.orchestrator.register(Action(Capability.BACKGROUND_JOBS, "scheduler.active", lambda: self._tool("scheduler").active()))
        self.orchestrator.register(Action(Capability.CLOUD_ROUTING, "cloud_router.complete", lambda messages: self._tool("cloud_router").complete(messages)))
        self.orchestrator.register(Action(Capability.ACCOUNT_READ, "accounts.list", lambda: self._tool("account_manager").list_accounts()))
        self.orchestrator.register(Action(Capability.ACCOUNT_READ, "accounts.select", lambda provider, account_id=None, label=None: self._select_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.connect", lambda provider, login_hint=None: self._connect_account(provider, login_hint=login_hint)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.refresh", lambda provider, account_id=None, label=None: self._refresh_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.disconnect", lambda provider, account_id=None, label=None: self._disconnect_account(provider, account_id=account_id, label=label)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.service_action", lambda operation, provider, account_id=None, label=None, payload=None, confirmed=False: self._service_account_action(operation, provider, account_id=account_id, label=label, payload=payload, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.ACCOUNT_WRITE, "accounts.github_fork", lambda repository, account_id="primary", organization=None: self._github_fork(repository, account_id=account_id, organization=organization)))
        self.orchestrator.register(Action(Capability.REPO_WRITE, "self_coding.run", lambda goal: self._tool("self_coding").run(goal)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.search", lambda query: self._tool("gods_eye").search(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.locate_me", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.open_place", lambda query: self._open_place(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "gods_eye.route_to", lambda query: self._route_to(query)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.current", lambda: self._tool("gods_eye").locate_me()))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.save", lambda name, latitude, longitude, address=None, accuracy_m=None, source="user", confirmed=False: self._save_location(name, latitude, longitude, address=address, accuracy_m=accuracy_m, source=source, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.save_current", lambda name, address=None, confirmed=False: self._save_current_location(name, address=address, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.get", lambda name: self._tool("locations").get(name)))
        self.orchestrator.register(Action(Capability.LOCATION_READ, "locations.list", lambda: self._tool("locations").list()))
        self.orchestrator.register(Action(Capability.LOCATION_WRITE, "locations.delete", lambda name, confirmed=False: self._delete_saved_location(name, confirmed=confirmed)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.list", lambda: self._tool("devices").list()))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.refresh", lambda: self._tool("devices").refresh()))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.state", lambda device_id: self._tool("devices").state(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.select", lambda device_id: self._tool("devices").select(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_READ, "devices.active", lambda: self._tool("devices").active()))
        self.orchestrator.register(Action(Capability.DEVICE_SCREEN, "devices.screen", lambda device_id: self._tool("devices").screen(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_INPUT, "devices.input", lambda device_id, kind, **kwargs: self._tool("devices").input(device_id, kind, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_NOTIFICATIONS, "devices.notifications", lambda device_id: self._tool("devices").notifications(device_id)))
        self.orchestrator.register(Action(Capability.DEVICE_FILES, "devices.files", lambda device_id, direction, path, **kwargs: self._tool("devices").transfer(device_id, direction, path, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_APPS, "devices.apps", lambda device_id, app_id, **kwargs: self._tool("devices").open_app(device_id, app_id, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_AUTOMATION, "devices.automate", lambda device_id, steps, **kwargs: self._tool("devices").automate(device_id, steps, confirmed=True, **kwargs)))
        self.orchestrator.register(Action(Capability.DEVICE_INPUT, "devices.hand_target", lambda device_id: self._set_hand_target(device_id)))

    def _start_hand_control(self) -> Any:
        return self._tool("hand_control").start()

    def _stop_hand_control(self) -> Any:
        return self._tool("hand_control").stop()

    def _set_hand_target(self, device_id: str | None) -> Any:
        if device_id is not None and self._tool("devices").registry.provider_for(device_id) is None:
            raise LookupError(f"No device found for: {device_id}")
        self._tool("hand_control").set_device_target(device_id)
        return {"target_device_id": device_id}

    def _select_account(self, provider: str, *, account_id: str | None = None, label: str | None = None) -> Any:
        return self._tool("account_manager").select_account(provider, account_id=account_id, label=label)

    def _connect_account(self, provider: str, *, login_hint: str | None = None) -> Any:
        return self._tool("account_manager").connect(provider, login_hint=login_hint)

    def _refresh_account(self, provider: str, *, account_id: str | None = None, label: str | None = None) -> Any:
        return self._tool("account_manager").refresh(provider, account_id=account_id, label=label)

    def _disconnect_account(self, provider: str, *, account_id: str | None = None, label: str | None = None) -> Any:
        return self._tool("account_manager").disconnect(provider, account_id=account_id, label=label)

    def _service_account_action(self, operation: str, provider: str, *, account_id: str | None = None, label: str | None = None, payload: dict[str, Any] | None = None, confirmed: bool = False) -> Any:
        return self._tool("account_manager").service_action(operation, provider, account_id=account_id, label=label, payload=payload, confirmed=confirmed)

    def _github_fork(self, repository: str, *, account_id: str = "primary", organization: str | None = None) -> Any:
        return self._tool("account_access").github_fork(repository, account_id=account_id, organization=organization)

    def _first_place(self, query: str) -> tuple[Any, Place]:
        places = self._tool("gods_eye").search(query)
        if not places:
            raise LookupError(f"No place found for: {query}")
        return query, places[0]

    def _open_place(self, query: str) -> Any:
        return self._tool("gods_eye").open_place(query)

    def _route_to(self, query: str) -> Any:
        return self._tool("gods_eye").route_to(query)

    def _save_location(self, name: str, latitude: float, longitude: float, *, address: str | None = None, accuracy_m: float | None = None, source: str = "user", confirmed: bool = False) -> Any:
        if not confirmed:
            raise PermissionError("Saving a location requires confirmation")
        from .gods_eye import GeoPoint
        return self._tool("locations").save(name, GeoPoint(float(latitude), float(longitude)), address=address, accuracy_m=accuracy_m, source=source)

    def _save_current_location(self, name: str, *, address: str | None = None, confirmed: bool = False) -> Any:
        if not confirmed:
            raise PermissionError("Saving the current location requires confirmation")
        snapshot = self._tool("gods_eye").locate_me()
        return self._tool("locations").save_current(name, snapshot, address=address)

    def _delete_saved_location(self, name: str, *, confirmed: bool = False) -> bool:
        if not confirmed:
            raise PermissionError("Deleting a saved location requires confirmation")
        return self._tool("locations").delete(name)

    def _resolve_device(self, reference: str) -> str:
        value = reference.strip()
        if not value:
            raise ValueError("device reference must not be empty")
        devices = list(self._tool("devices").list())
        exact = [d for d in devices if d.device_id == value]
        if exact:
            return exact[0].device_id
        matches = [d for d in devices if d.label.casefold() == value.casefold()]
        if len(matches) == 1:
            return matches[0].device_id
        if len(matches) > 1:
            raise ValueError(f"Multiple devices match: {reference}")
        raise LookupError(f"No device found for: {reference}")

    def dispatch(self, capability: Capability, operation: str, *args: Any, **kwargs: Any) -> Any:
        return self.orchestrator.run(capability, operation, *args, confirmation=self.confirmation, **kwargs)

    def handle_assistant_request(self, text: str, confirmed: bool = False) -> dict[str, Any]:
        result = self._assistant_orchestrator().execute(text, confirmed=confirmed)
        return {"text": result.text, "profile": result.profile, "verified": result.verified, "needs_confirmation": result.needs_confirmation, "parallel_tasks_completed": result.parallel_tasks_completed, "providers": result.providers, "latency_ms": result.latency_ms, "errors": result.errors}

    def handle_assistant_stream(self, text: str, confirmed: bool = False) -> Iterator[Any]:
        yield from self._assistant_orchestrator().execute_stream(text, confirmed=confirmed)

    def handle_text(self, text: str) -> Any:
        intent: Intent = parse_intent(text)
        if intent.kind == "hand_control_start":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "hand_control.start")}
        if intent.kind == "hand_control_stop":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "hand_control.stop")}
        if intent.kind == "device_hand_target":
            reference = intent.arguments.get("device")
            device_id = self._resolve_device(str(reference)) if reference else None
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_INPUT, "devices.hand_target", device_id)}
        if intent.kind == "device_list":
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.list")}
        if intent.kind == "device_refresh":
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.refresh")}
        if intent.kind == "device_select":
            device_id = self._resolve_device(str(intent.arguments["device"]))
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_READ, "devices.select", device_id)}
        if intent.kind == "device_screen":
            reference = intent.arguments.get("device")
            if reference:
                device_id = self._resolve_device(str(reference))
            else:
                active = self.dispatch(Capability.DEVICE_READ, "devices.active")
                if not active.ok:
                    return {"intent": intent, "result": active}
                device_id = active.data["state"].device_id
            return {"intent": intent, "result": self.dispatch(Capability.DEVICE_SCREEN, "devices.screen", device_id)}
        if intent.kind == "browser_open":
            browser = str(intent.arguments["browser"])
            url = intent.arguments.get("url")
            if url:
                return {"intent": intent, "result": self.dispatch(Capability.BROWSER_CONTROL, "browser.open_url", url=str(url), browser=browser)}
            return {"intent": intent, "result": self.dispatch(Capability.BROWSER_CONTROL, "browser.start", browser=browser)}
        if intent.kind == "application_list":
            return {"intent": intent, "result": self.dispatch(Capability.APP_READ, "applications.list")}
        if intent.kind == "application_uninstall":
            return {"intent": intent, "result": self.dispatch(Capability.APP_WRITE, "applications.uninstall", name=str(intent.arguments["name"]))}
        if intent.kind == "process_list":
            return {"intent": intent, "result": self.dispatch(Capability.PROCESS_READ, "processes.list")}
        if intent.kind == "system_inspect":
            return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_DIAGNOSTICS, "system.inspect")}
        if intent.kind == "file_read":
            return {"intent": intent, "result": self.dispatch(Capability.FILE_READ, "files.read", path=str(intent.arguments["path"]))}
        if intent.kind == "file_delete":
            return {"intent": intent, "result": self.dispatch(Capability.FILE_DELETE, "files.delete", path=str(intent.arguments["path"]))}
        if intent.kind == "place_search":
            query = str(intent.arguments["query"])
            result = self.dispatch(Capability.LOCATION_READ, "gods_eye.open_place", query=query)
            self.gods_eye_launcher.launch_query(query)
            return {"intent": intent, "result": result, "opened": True}
        if intent.kind == "locate_me":
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_READ, "gods_eye.locate_me")}
        if intent.kind == "route":
            query = str(intent.arguments["query"])
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_READ, "gods_eye.route_to", query=query)}
        if intent.kind == "save_current_location":
            name = str(intent.arguments["name"])
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.save_current", name=name)}
        if intent.kind == "save_place":
            place_query = str(intent.arguments["place"])
            name = str(intent.arguments["name"])
            place = self._first_place(place_query)[1]
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.save", name=name, latitude=place.point.latitude, longitude=place.point.longitude, source=place.provider)}
        if intent.kind == "saved_location":
            saved = self.dispatch(Capability.LOCATION_READ, "locations.get", name=str(intent.arguments["name"]))
            if saved is None:
                raise LookupError(f"No saved location found for: {intent.arguments['name']}")
            return {"intent": intent, "result": saved}
        if intent.kind == "delete_saved_location":
            return {"intent": intent, "result": self.dispatch(Capability.LOCATION_WRITE, "locations.delete", name=str(intent.arguments["name"]))}
        if intent.kind == "screen_read":
            return {"intent": intent, "result": self.dispatch(Capability.SCREEN_READ, "screen.capture")}
        if intent.kind == "computer_action":
            return {"intent": intent, "result": self.dispatch(Capability.MOUSE_CONTROL, "computer.move", x=intent.arguments["x"], y=intent.arguments["y"])}
        if intent.kind == "windows_maintenance":
            request = str(intent.arguments["request"])
            if "diagnos" in request.casefold() and not any(word in request.casefold() for word in ("fix", "repair", "clean")):
                return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_DIAGNOSTICS, "windows_maintenance.diagnose")}
            return {"intent": intent, "result": self.dispatch(Capability.SYSTEM_MAINTENANCE, "windows_maintenance.handle", request=request)}
        return intent
