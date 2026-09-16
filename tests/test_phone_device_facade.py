import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.facade import DeviceFacade
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.provider import DeviceInputEvent
from quality_of_life.devices.registry import DeviceRegistry
from quality_of_life.permissions import Capability, CapabilityDenied, CapabilityPolicy


class PhoneFacadeTests(unittest.TestCase):
    def setUp(self):
        provider = FakePhoneProvider()
        provider.add_device(
            DeviceState("phone", "Main Phone", True, 80),
            frozenset({DeviceCapability.STATE_READ, DeviceCapability.SCREEN_VIEW, DeviceCapability.INPUT_CONTROL}),
        )
        registry = DeviceRegistry([provider])
        registry.refresh()
        self.provider = provider
        self.facade = DeviceFacade(
            registry,
            CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ, Capability.DEVICE_SCREEN, Capability.DEVICE_INPUT})),
            confirmation=lambda _: True,
        )

    def test_reads_state_and_screen(self):
        self.assertTrue(self.facade.state("phone").ok)
        self.assertTrue(self.facade.screen("phone").ok)

    def test_screen_all_starts_every_connected_phone(self):
        self.provider.add_device(
            DeviceState("phone-two", "Second Phone", True, 70),
            frozenset({DeviceCapability.STATE_READ, DeviceCapability.SCREEN_VIEW}),
        )
        registry = DeviceRegistry([self.provider])
        registry.refresh()
        facade = DeviceFacade(
            registry,
            CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ, Capability.DEVICE_SCREEN})),
        )
        results = facade.screen_all()
        self.assertEqual([result.code for result in results], ["OK", "OK"])
        self.assertEqual(
            [record["device_id"] for record in self.provider.operations if record["operation"] == "screen"],
            ["phone", "phone-two"],
        )

    def test_mutation_requires_permission(self):
        facade = DeviceFacade(
            self.facade.registry,
            CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ})),
        )
        with self.assertRaises(CapabilityDenied):
            facade.input("phone", DeviceInputEvent("tap", 1, 2))

    def test_confirmation_is_enforced_for_input(self):
        facade = DeviceFacade(
            self.facade.registry,
            CapabilityPolicy(allowed=frozenset({Capability.DEVICE_INPUT})),
            confirmation=lambda _: False,
        )
        with self.assertRaises(CapabilityDenied):
            facade.input("phone", DeviceInputEvent("tap", 1, 2))
        self.assertTrue(self.facade.input("phone", DeviceInputEvent("tap", 1, 2)).ok)


if __name__ == "__main__":
    unittest.main()
