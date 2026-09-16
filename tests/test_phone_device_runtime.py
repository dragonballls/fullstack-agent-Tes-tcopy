import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.runtime import DeviceTool
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneDeviceRuntimeTests(unittest.TestCase):
    def test_device_tool_accepts_injected_provider_without_platform_dependency(self):
        provider = FakePhoneProvider()
        provider.add_device(
            DeviceState("phone", "Main Phone", True, 77),
            frozenset({DeviceCapability.STATE_READ}),
        )
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ}))
        tool = DeviceTool(policy, providers=(provider,))
        self.assertEqual([d.device_id for d in tool.list()], ["phone"])
        self.assertTrue(tool.state("phone").ok)

    def test_empty_runtime_is_safe_when_adb_is_unavailable(self):
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ}))
        tool = DeviceTool(policy, providers=())
        self.assertEqual(tool.list(), ())


if __name__ == "__main__":
    unittest.main()
