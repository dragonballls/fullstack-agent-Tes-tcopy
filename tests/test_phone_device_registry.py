import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.models import DeviceState
from quality_of_life.devices.registry import DeviceRegistry


class PhoneRegistryTests(unittest.TestCase):
    def test_registers_selects_and_removes_multiple_devices(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("a", "Main", True, 90))
        provider.add_device(DeviceState("b", "Spare", True, 50))
        registry = DeviceRegistry([provider])
        result = registry.refresh()
        self.assertTrue(result.ok)
        self.assertEqual({d.device_id for d in registry.list()}, {"a", "b"})
        self.assertEqual(registry.select("b").data["device_id"], "b")
        self.assertEqual(registry.active().data["state"].device_id, "b")
        self.assertTrue(registry.remove("b").ok)
        self.assertEqual(registry.active().data["state"].device_id, "a")

    def test_unknown_selection_is_rejected(self):
        registry = DeviceRegistry()
        registry.refresh()
        result = registry.select("missing")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "NOT_FOUND")

    def test_duplicate_provider_ids_are_rejected(self):
        left = FakePhoneProvider(name="left")
        right = FakePhoneProvider(name="right")
        left.add_device(DeviceState("same", "A", True))
        right.add_device(DeviceState("same", "B", True))
        registry = DeviceRegistry([left, right])
        result = registry.refresh()
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "DUPLICATE_ID")

    def test_transient_provider_error_keeps_last_known_devices(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("a", "Main", True, 90))
        registry = DeviceRegistry([provider])
        self.assertTrue(registry.refresh().ok)
        original = provider.list_devices
        provider.list_devices = lambda: (_ for _ in ()).throw(RuntimeError("temporary"))
        result = registry.refresh()
        self.assertTrue(result.ok)
        self.assertEqual([d.device_id for d in registry.list()], ["a"])
        provider.list_devices = original


if __name__ == "__main__":
    unittest.main()
