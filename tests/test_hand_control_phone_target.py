import unittest
from types import SimpleNamespace

from quality_of_life.hand_control import HandControlBridge, HandEvent


class FakeAdapter:
    def __init__(self):
        self.calls = []
    def route_hand_event(self, device_id, event, *, confirmed=False):
        self.calls.append((device_id, event.kind, event.x, event.y, confirmed))
        return SimpleNamespace(ok=True)


class HandControlPhoneTargetTests(unittest.TestCase):
    def test_targeted_hand_events_use_device_adapter(self):
        adapter = FakeAdapter()
        bridge = HandControlBridge(enabled=True, controller=None, device_adapter=adapter, target_device_id="phone-1")
        self.assertTrue(bridge.dispatch(HandEvent("move", x=.2, y=.3)))
        self.assertTrue(bridge.dispatch(HandEvent("click")))
        self.assertEqual(adapter.calls[0], ("phone-1", "move", .2, .3, True))
        self.assertEqual(adapter.calls[1][0:2], ("phone-1", "click"))

    def test_pause_disables_targeted_hand_control(self):
        adapter = FakeAdapter()
        bridge = HandControlBridge(enabled=True, device_adapter=adapter, target_device_id="phone-1")
        self.assertTrue(bridge.dispatch(HandEvent("pause")))
        self.assertFalse(bridge.dispatch(HandEvent("move", x=.2, y=.3)))
        self.assertEqual(adapter.calls, [])


if __name__ == "__main__":
    unittest.main()
