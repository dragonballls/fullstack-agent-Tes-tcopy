import unittest

from quality_of_life.capabilities import OperationRisk, operation
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneDevicePermissionTests(unittest.TestCase):
    def test_catalog_contains_all_core_device_operations(self):
        expected = {
            "devices.list": Capability.DEVICE_READ,
            "devices.state": Capability.DEVICE_READ,
            "devices.select": Capability.DEVICE_READ,
            "devices.screen": Capability.DEVICE_SCREEN,
            "devices.screen_all": Capability.DEVICE_SCREEN,
            "devices.input": Capability.DEVICE_INPUT,
            "devices.notifications": Capability.DEVICE_NOTIFICATIONS,
            "devices.files": Capability.DEVICE_FILES,
            "devices.apps": Capability.DEVICE_APPS,
            "devices.automate": Capability.DEVICE_AUTOMATION,
        }
        for name, capability in expected.items():
            spec = operation(name)
            self.assertEqual(spec.capability, capability)
        self.assertEqual(operation("devices.input").risk, OperationRisk.MUTATE)
        self.assertEqual(operation("devices.screen").risk, OperationRisk.READ)
        self.assertEqual(operation("devices.screen_all").risk, OperationRisk.READ)

    def test_mutating_device_capabilities_require_confirmation(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_INPUT, Capability.DEVICE_FILES, Capability.DEVICE_APPS, Capability.DEVICE_AUTOMATION}))
        self.assertTrue(policy.needs_confirmation(Capability.DEVICE_INPUT))
        self.assertTrue(policy.needs_confirmation(Capability.DEVICE_FILES))
        self.assertTrue(policy.needs_confirmation(Capability.DEVICE_APPS))
        self.assertTrue(policy.needs_confirmation(Capability.DEVICE_AUTOMATION))
        self.assertFalse(policy.needs_confirmation(Capability.DEVICE_READ))


if __name__ == "__main__":
    unittest.main()
