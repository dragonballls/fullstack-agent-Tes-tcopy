import unittest
from types import SimpleNamespace

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.facade import DeviceFacade
from quality_of_life.devices.input_adapter import DeviceInputAdapter
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.registry import DeviceRegistry
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneDeviceInputTests(unittest.TestCase):
    def _facade(self, provider):
        registry = DeviceRegistry([provider])
        registry.refresh()
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_INPUT, Capability.DEVICE_READ}))
        return DeviceFacade(registry, policy, confirmation=lambda _: True)

    def test_routes_gesture_style_event_to_selected_phone(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ, DeviceCapability.INPUT_CONTROL}))
        result = DeviceInputAdapter(self._facade(provider)).route("phone", "tap", x=100, y=200)
        self.assertTrue(result.ok)
        self.assertEqual(provider.operations[-1][0], "input")

    def test_hand_move_tracks_phone_point_without_inventing_hover_input(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ, DeviceCapability.INPUT_CONTROL}), display_size=(1000, 2000))
        adapter = DeviceInputAdapter(self._facade(provider))
        moved = adapter.route_hand_event("phone", SimpleNamespace(kind="move", x=0.25, y=0.5), confirmed=True)
        self.assertTrue(moved.ok)
        self.assertEqual(provider.operations, [])
        clicked = adapter.route_hand_event("phone", SimpleNamespace(kind="click"), confirmed=True)
        self.assertTrue(clicked.ok)
        event = provider.operations[-1][2]
        self.assertEqual((event.x, event.y), (250, 1000))

    def test_hand_click_without_point_is_rejected(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ, DeviceCapability.INPUT_CONTROL}))
        result = DeviceInputAdapter(self._facade(provider)).route_hand_event("phone", SimpleNamespace(kind="click"), confirmed=True)
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "NO_POINT")


if __name__ == "__main__":
    unittest.main()
