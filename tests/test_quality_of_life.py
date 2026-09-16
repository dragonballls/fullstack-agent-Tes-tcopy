import unittest

from quality_of_life.manifest import default_registry
from quality_of_life.orchestrator import Action, QoLOrchestrator
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy


class QualityOfLifeTests(unittest.TestCase):
    def test_capabilities_are_denied_by_default(self) -> None:
        with self.assertRaises(CapabilityDenied):
            CapabilityPolicy().check(Capability.MOUSE_CONTROL)

    def test_default_registry_names_are_stable(self) -> None:
        self.assertEqual(
            default_registry().names(),
            ("account_access", "account_integrations", "account_manager", "applications", "background", "browser", "browser_registry", "clipboard", "cloud_router", "computer", "devices", "files", "gods_eye", "hand_control", "hand_control_runtime", "hand_control_server", "locations", "processes", "scheduler", "screen", "self_coding", "service_adapters", "system", "voice_listener", "windows", "windows_maintenance"),
        )

    def test_orchestrator_checks_policy(self) -> None:
        policy = CapabilityPolicy(allowed=frozenset({Capability.CLIPBOARD}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator.register(Action(Capability.CLIPBOARD, "echo", lambda value: value))
        self.assertEqual(orchestrator.run(Capability.CLIPBOARD, "echo", "ok"), "ok")

    def test_disabled_mutation_is_rejected_before_execution(self) -> None:
        calls = []
        policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator.register(Action(Capability.MOUSE_CONTROL, "move", lambda: calls.append("called")))
        with self.assertRaises(PermissionError):
            orchestrator.run(Capability.MOUSE_CONTROL, "move", confirmation=lambda *_: False)
        self.assertEqual(calls, [])

    def test_confirmation_denial_prevents_execution(self) -> None:
        calls = []
        policy = CapabilityPolicy(allowed=frozenset({Capability.BACKGROUND_JOBS}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator.register(Action(Capability.BACKGROUND_JOBS, "mutate", lambda: calls.append("called")))
        with self.assertRaises(PermissionError):
            orchestrator.run(Capability.BACKGROUND_JOBS, "mutate", confirmation=lambda *_: False)
        self.assertEqual(calls, [])

    def test_mutation_requires_confirmation_and_executes_after_approval(self) -> None:
        calls = []
        policy = CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator.register(Action(Capability.MOUSE_CONTROL, "move", lambda: calls.append("called")))
        orchestrator.run(Capability.MOUSE_CONTROL, "move", confirmation=lambda *_: True)
        self.assertEqual(calls, ["called"])

    def test_fake_desktop_adapter_calls_pyautogui(self) -> None:
        class FakePyAutoGUI:
            def __init__(self): self.calls = []
            def moveTo(self, *args, **kwargs): self.calls.append(("moveTo", args))
            def click(self, *args, **kwargs): self.calls.append(("click", args))
            def scroll(self, *args, **kwargs): self.calls.append(("scroll", args))
            def write(self, *args, **kwargs): self.calls.append(("write", args))
            def hotkey(self, *args, **kwargs): self.calls.append(("hotkey", args))

        fake = FakePyAutoGUI()
        from quality_of_life import computer
        controller = computer.ComputerController(
            CapabilityPolicy(allowed=frozenset({Capability.MOUSE_CONTROL, Capability.KEYBOARD_CONTROL})),
            pyautogui=fake,
        )
        controller.move(1, 2)
        controller.click()
        controller.scroll(3)
        controller.type_text("x")
        controller.hotkey("ctrl", "c")
