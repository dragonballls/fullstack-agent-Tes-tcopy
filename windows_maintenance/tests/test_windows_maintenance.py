import unittest
from unittest.mock import patch

from windows_maintenance.models import MaintenanceAction
from windows_maintenance.policy import MaintenancePolicy


class WindowsMaintenanceTests(unittest.TestCase):
    def test_module_contract(self):
        action = MaintenanceAction("process.stop", "steam.exe")
        self.assertTrue(MaintenancePolicy().evaluate(action, explicit_user_request=True).allowed)

    @patch("windows_maintenance.windows._require_windows")
    @patch("windows_maintenance.windows._ps")
    def test_process_stop_verifies_identity_command(self, ps, _require_windows):
        ps.return_value = False
        from windows_maintenance import windows

        ok, detail = windows.stop_process(123, "safe-name")
        self.assertTrue(ok)
        self.assertIn("verified", detail)
        script = ps.call_args.args[0]
        self.assertIn("safe-name", script)
        self.assertIn("Stop-Process", script)
        self.assertIn("ProcessName", script)

    def test_policy_protects_windows_and_agent_processes(self):
        policy = MaintenancePolicy()
        self.assertTrue(policy.is_protected_process("svchost"))
        self.assertTrue(policy.is_protected_process("Jarvis"))
        self.assertTrue(policy.is_protected_process("thing", r"C:\Windows\System32\thing.exe"))
        self.assertFalse(policy.is_protected_process("Steam", r"C:\Games\Steam\steam.exe"))

    def test_high_risk_requires_confirmation(self):
        action = MaintenanceAction("network.reset", "windows", risk="HIGH_RISK")
        policy = MaintenancePolicy(allow_high_risk=True)
        decision = policy.evaluate(action, explicit_user_request=True, confirmed=False)
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_confirmation)


if __name__ == "__main__":
    unittest.main()

# CI verification marker: exercise all push-triggered validation workflows.
