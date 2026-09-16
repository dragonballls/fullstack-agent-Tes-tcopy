import threading
import unittest

from quality_of_life.devices.automation import DeviceAutomation
from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.facade import DeviceFacade
from quality_of_life.devices.models import DeviceCapability, DeviceResult, DeviceState
from quality_of_life.devices.registry import DeviceRegistry
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneAutomationTests(unittest.TestCase):
    def test_successful_targeted_action(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ}))
        registry = DeviceRegistry([provider])
        registry.refresh()
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ, Capability.DEVICE_AUTOMATION}))
        facade = DeviceFacade(registry, policy)
        automation = DeviceAutomation(facade, policy)
        result = automation.run("phone", lambda _cancel: DeviceResult.success("ran"))
        self.assertTrue(result.ok)
        self.assertEqual(result.message, "ran")

    def test_cancellation_stops_before_action(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ}))
        registry = DeviceRegistry([provider])
        registry.refresh()
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ, Capability.DEVICE_AUTOMATION}))
        facade = DeviceFacade(registry, policy)
        automation = DeviceAutomation(facade, policy)
        cancel = threading.Event()
        cancel.set()
        result = automation.run("phone", lambda _cancel: DeviceResult.success(), cancel)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "CANCELLED")

    def test_disconnect_during_action_is_reported(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ}))
        registry = DeviceRegistry([provider])
        registry.refresh()
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ, Capability.DEVICE_AUTOMATION}))
        facade = DeviceFacade(registry, policy)

        def action(_cancel):
            provider.devices["phone"] = DeviceState("phone", "Main", False)
            return DeviceResult.success("ran")

        result = DeviceAutomation(facade, policy).run("phone", action)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DISCONNECTED")


if __name__ == "__main__":
    unittest.main()
