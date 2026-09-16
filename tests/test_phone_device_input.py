import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.facade import DeviceFacade
from quality_of_life.devices.input_adapter import DeviceInputAdapter
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.registry import DeviceRegistry
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneDeviceInputTests(unittest.TestCase):
    def test_routes_gesture_style_event_to_selected_phone(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ, DeviceCapability.INPUT_CONTROL}))
        registry = DeviceRegistry([provider])
        registry.refresh()
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_INPUT, Capability.DEVICE_READ}))
        facade = DeviceFacade(registry, policy, confirmation=lambda _: True)
        result = DeviceInputAdapter(facade).route("phone", "tap", x=100, y=200)
        self.assertTrue(result.ok)
        self.assertEqual(provider.operations[-1][0], "input")


if __name__ == "__main__":
    unittest.main()
