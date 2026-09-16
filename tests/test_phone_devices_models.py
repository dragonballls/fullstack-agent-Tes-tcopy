import unittest

from quality_of_life.devices.models import DeviceCapability, DeviceResult, DeviceState
from quality_of_life.devices.provider import DeviceInputEvent


class PhoneDeviceModelsTests(unittest.TestCase):
    def test_state_validates_identity_and_battery(self):
        state = DeviceState("phone-1", "Main Phone", True, 73, False, "fake")
        self.assertEqual(state.device_id, "phone-1")
        with self.assertRaises(ValueError):
            DeviceState("", "Main Phone", True)
        with self.assertRaises(ValueError):
            DeviceState("phone-1", "Main Phone", True, 101)

    def test_result_helpers_are_explicit(self):
        ok = DeviceResult.success("done", value=1)
        failure = DeviceResult.failure("UNAVAILABLE", "not supported")
        self.assertTrue(ok.ok)
        self.assertEqual(ok.data["value"], 1)
        self.assertFalse(failure.ok)
        self.assertEqual(failure.code, "UNAVAILABLE")

    def test_input_event_requires_kind(self):
        self.assertEqual(DeviceInputEvent("tap", x=0.5, y=0.2).kind, "tap")
        with self.assertRaises(ValueError):
            DeviceInputEvent("")

    def test_capability_values_are_stable(self):
        self.assertEqual(DeviceCapability.SCREEN_VIEW.value, "screen.view")
        self.assertEqual(DeviceCapability.INPUT_CONTROL.value, "input.control")


if __name__ == "__main__":
    unittest.main()
