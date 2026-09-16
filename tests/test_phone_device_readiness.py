import unittest
from unittest.mock import patch

from quality_of_life.devices.readiness import check_readiness


class PhoneDeviceReadinessTests(unittest.TestCase):
    @patch("quality_of_life.devices.readiness.shutil.which")
    def test_reports_adb_and_scrcpy_independently(self, which):
        which.side_effect = lambda name: "/tools/adb.exe" if name == "adb" else None
        readiness = check_readiness()
        self.assertTrue(readiness.adb.available)
        self.assertFalse(readiness.scrcpy.available)
        self.assertFalse(readiness.ready_for_live_screen)
        self.assertTrue(readiness.ready_for_direct_android)
        self.assertFalse(readiness.phone_link.available)


if __name__ == "__main__":
    unittest.main()
