import unittest

from quality_of_life.devices.models import DeviceCapability
from quality_of_life.devices.phone_link import PhoneLinkProvider, UnavailablePhoneLinkBridge


class PhoneLinkAdapterTests(unittest.TestCase):
    def test_default_bridge_is_safe_and_importable(self):
        provider = PhoneLinkProvider()
        self.assertEqual(tuple(provider.list_devices()), ())
        result = provider.view_screen("missing")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")
        self.assertNotIn(DeviceCapability.SCREEN_VIEW, provider.capabilities("missing"))

    def test_unavailable_bridge_is_explicit(self):
        bridge = UnavailablePhoneLinkBridge("Phone Link not configured")
        result = bridge.open_app("phone", "com.example")
        self.assertFalse(result.ok)
        self.assertEqual(result.message, "Phone Link not configured")


if __name__ == "__main__":
    unittest.main()
