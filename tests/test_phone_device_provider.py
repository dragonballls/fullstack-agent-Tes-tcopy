import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.provider import DeviceInputEvent


class PhoneProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakePhoneProvider()
        self.provider.add_device(
            DeviceState("phone-1", "Main Phone", True, 80, True, "fake"),
            frozenset({
                DeviceCapability.STATE_READ,
                DeviceCapability.SCREEN_VIEW,
                DeviceCapability.INPUT_CONTROL,
                DeviceCapability.NOTIFICATION_READ,
                DeviceCapability.FILES,
                DeviceCapability.APP_CONTROL,
            }),
        )
        self.provider.add_device(
            DeviceState("phone-2", "Spare Phone", False, 20, False, "fake"),
            frozenset({DeviceCapability.STATE_READ}),
        )

    def test_lists_multiple_devices(self):
        self.assertEqual({d.device_id for d in self.provider.list_devices()}, {"phone-1", "phone-2"})

    def test_supported_operation_is_recorded(self):
        result = self.provider.send_input("phone-1", DeviceInputEvent("tap", x=.5, y=.5))
        self.assertTrue(result.ok)
        self.assertEqual(self.provider.operations[-1][0], "input")

    def test_unsupported_capability_is_explicit(self):
        result = self.provider.view_screen("phone-2")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DISCONNECTED")
        result = self.provider.read_notifications("phone-2")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DISCONNECTED")

    def test_unknown_device_is_explicit(self):
        result = self.provider.get_state("missing")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
