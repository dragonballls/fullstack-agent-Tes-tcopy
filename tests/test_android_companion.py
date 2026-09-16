import subprocess
import unittest

from quality_of_life.devices.android_companion import AndroidCompanionClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self, limit):
        return self.payload


class AndroidCompanionClientTests(unittest.TestCase):
    def test_forwards_each_physical_device_to_its_own_local_port(self):
        calls = []
        def runner(args):
            calls.append(tuple(args))
            return subprocess.CompletedProcess(args, 0, "", "")
        def opener(request, timeout=2.0):
            return FakeResponse(b'{"ok":true,"message":"ready","notifications":[]}')

        client = AndroidCompanionClient("adb", runner=runner, opener=opener)
        self.assertTrue(client.health("phone-a").ok)
        self.assertTrue(client.notifications("phone-a").ok)
        self.assertTrue(client.health("phone-b").ok)
        forwards = [call for call in calls if "forward" in call]
        self.assertIn("tcp:18765", forwards[0])
        self.assertIn("tcp:18766", forwards[-1])
        self.assertEqual(len({call for call in forwards}), 2)

    def test_failed_forward_is_explicit(self):
        def runner(args):
            return subprocess.CompletedProcess(args, 1, "", "offline")
        client = AndroidCompanionClient("adb", runner=runner, opener=lambda *args, **kwargs: None)
        result = client.health("phone-a")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")

    def test_failed_companion_response_is_explicit(self):
        def runner(args):
            return subprocess.CompletedProcess(args, 0, "", "")
        client = AndroidCompanionClient("adb", runner=runner, opener=lambda *args, **kwargs: FakeResponse(b'{"ok":false,"code":"UNAVAILABLE","message":"listener disabled"}'))
        result = client.notifications("phone-a")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
