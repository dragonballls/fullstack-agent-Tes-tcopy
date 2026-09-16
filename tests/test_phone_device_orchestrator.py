import unittest

from quality_of_life.devices.fake_provider import FakePhoneProvider
from quality_of_life.devices.models import DeviceCapability, DeviceState
from quality_of_life.devices.runtime import DeviceTool
from quality_of_life.orchestrator import QoLOrchestrator
from quality_of_life.permissions import Capability, CapabilityPolicy


class PhoneDeviceOrchestratorTests(unittest.TestCase):
    def test_device_actions_use_existing_capability_gate(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True, 95), frozenset({DeviceCapability.STATE_READ}))
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator._device_tool = DeviceTool(policy, providers=(provider,))
        listed = orchestrator.run(Capability.DEVICE_READ, "devices.list")
        self.assertEqual([item.device_id for item in listed], ["phone"])
        state = orchestrator.run(Capability.DEVICE_READ, "devices.state", "phone")
        self.assertTrue(state.ok)

    def test_input_is_still_denied_without_device_input_capability(self):
        provider = FakePhoneProvider()
        provider.add_device(DeviceState("phone", "Main", True), frozenset({DeviceCapability.STATE_READ, DeviceCapability.INPUT_CONTROL}))
        policy = CapabilityPolicy(allowed=frozenset({Capability.DEVICE_READ}))
        orchestrator = QoLOrchestrator(policy)
        orchestrator._device_tool = DeviceTool(policy, providers=(provider,))
        with self.assertRaises(PermissionError):
            orchestrator.run(Capability.DEVICE_INPUT, "devices.input", "phone", "tap", x=1, y=2)


if __name__ == "__main__":
    unittest.main()
