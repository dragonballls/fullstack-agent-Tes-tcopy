import subprocess
import unittest

from quality_of_life.devices.android_adb import AndroidAdbProvider
from quality_of_life.devices.models import DeviceCapability
from quality_of_life.devices.provider import DeviceInputEvent, FileTransferDirection


class AndroidAdbProviderTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def runner(args):
            self.calls.append(tuple(args))
            if args[1:] == ("devices",):
                return subprocess.CompletedProcess(args, 0, "List of devices attached\nABC123\tdevice\nXYZ999\toffline\n", "")
            if "dumpsys" in args:
                return subprocess.CompletedProcess(args, 0, "status: 2\nlevel: 91\n", "")
            if args[1:] == ("-s", "ABC123", "shell", "wm", "size"):
                return subprocess.CompletedProcess(args, 0, "Physical size: 1080x2400\n", "")
            return subprocess.CompletedProcess(args, 0, "done\n", "")

        self.provider = AndroidAdbProvider(adb="adb", scrcpy="scrcpy", runner=runner, enable_companion=False)

    def test_discovers_multiple_real_device_ids(self):
        devices = self.provider.list_devices()
        self.assertEqual({d.device_id for d in devices}, {"ABC123", "XYZ999"})
        self.assertTrue(next(d for d in devices if d.device_id == "ABC123").connected)
        self.assertFalse(next(d for d in devices if d.device_id == "XYZ999").connected)

    def test_reads_battery_state(self):
        result = self.provider.get_state("ABC123")
        self.assertTrue(result.ok)
        state = result.data["state"]
        self.assertEqual(state.battery_percent, 91)
        self.assertTrue(state.charging)

    def test_reads_display_size(self):
        self.assertEqual(self.provider.display_size("ABC123"), (1080, 2400))

    def test_input_and_app_commands_are_serialized_without_shell(self):
        self.assertTrue(self.provider.send_input("ABC123", DeviceInputEvent("tap", 10, 20)).ok)
        self.assertTrue(self.provider.send_input("ABC123", DeviceInputEvent("text", text="hello world")).ok)
        self.assertTrue(self.provider.open_app("ABC123", "com.example.app").ok)
        joined = [" ".join(call) for call in self.calls]
        self.assertTrue(any("shell input tap 10 20" in call for call in joined))
        self.assertTrue(any("shell input text hello%sworld" in call for call in joined))
        self.assertTrue(any("shell monkey -p com.example.app 1" in call for call in joined))

    def test_file_transfer_uses_adb(self):
        self.assertTrue(self.provider.transfer_file("ABC123", FileTransferDirection.TO_DEVICE, "photo.jpg").ok)
        self.assertTrue(self.provider.transfer_file("ABC123", FileTransferDirection.FROM_DEVICE, "/sdcard/photo.jpg").ok)

    def test_notification_api_is_explicitly_unavailable_without_companion(self):
        result = self.provider.read_notifications("ABC123")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")

    def test_live_screen_requires_scrcpy(self):
        no_screen = AndroidAdbProvider(adb="adb", scrcpy=None, runner=self.provider._runner, enable_companion=False)
        result = no_screen.view_screen("ABC123")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")
        self.assertIn(DeviceCapability.SCREEN_VIEW, self.provider.capabilities("ABC123"))
        self.assertNotIn(DeviceCapability.SCREEN_VIEW, no_screen.capabilities("ABC123"))


if __name__ == "__main__":
    unittest.main()
