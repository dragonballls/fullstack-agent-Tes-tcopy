import unittest

from quality_of_life.devices.mirror import MirrorSession, MultiDeviceMirrorManager


class FakeProcess:
    def __init__(self, pid):
        self.pid = pid
        self.terminated = False

    def poll(self):
        return 0 if self.terminated else None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.terminated = True
        return 0


class StubbornProcess(FakeProcess):
    def __init__(self, pid):
        super().__init__(pid)
        self.killed = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        if not self.killed:
            raise TimeoutError("process did not exit")
        return 0

    def kill(self):
        self.killed = True

    def poll(self):
        return 0 if self.killed else None


class MultiDeviceMirrorManagerTests(unittest.TestCase):
    def test_starts_independent_sessions_for_multiple_devices(self):
        processes = []

        def launcher(args):
            process = FakeProcess(len(processes) + 1)
            processes.append((tuple(args), process))
            return process

        manager = MultiDeviceMirrorManager(
            scrcpy="scrcpy",
            launcher=launcher,
            low_latency=True,
            window_layout=((0, 0, 540, 960), (540, 0, 540, 960)),
        )

        first = manager.start("phone-a", "Pixel A")
        second = manager.start("phone-b", "Pixel B")

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(set(manager.active_ids()), {"phone-a", "phone-b"})
        self.assertIsInstance(manager.get("phone-a"), MirrorSession)
        self.assertEqual(manager.get("phone-a").process.pid, 1)
        self.assertEqual(manager.get("phone-b").process.pid, 2)
        self.assertNotEqual(manager.get("phone-a").process.pid, manager.get("phone-b").process.pid)

        first_args = processes[0][0]
        second_args = processes[1][0]
        self.assertIn("--serial", first_args)
        self.assertIn("phone-a", first_args)
        self.assertIn("--serial", second_args)
        self.assertIn("phone-b", second_args)
        self.assertIn("--max-fps=60", first_args)
        self.assertIn("--video-codec=h264", first_args)
        self.assertIn("--window-title=Jarvis — Pixel A", first_args)
        self.assertIn("--window-x=0", first_args)
        self.assertIn("--window-width=540", first_args)
        self.assertIn("--window-x=540", second_args)

    def test_start_is_idempotent_for_live_session_and_stop_does_not_touch_other_phone(self):
        processes = []

        def launcher(args):
            process = FakeProcess(len(processes) + 1)
            processes.append((tuple(args), process))
            return process

        manager = MultiDeviceMirrorManager(scrcpy="scrcpy", launcher=launcher)
        first = manager.start("phone-a", "Pixel A")
        again = manager.start("phone-a", "Pixel A")
        second = manager.start("phone-b", "Pixel B")

        self.assertTrue(first.ok)
        self.assertTrue(again.ok)
        self.assertEqual(again.data["pid"], first.data["pid"])
        self.assertTrue(second.ok)
        self.assertEqual(len(processes), 2)

        stopped = manager.stop("phone-a")
        self.assertTrue(stopped.ok)
        self.assertTrue(processes[0][1].terminated)
        self.assertFalse(processes[1][1].terminated)
        self.assertEqual(manager.active_ids(), ("phone-b",))

    def test_stale_session_is_restarted_and_disconnect_can_close_all(self):
        processes = []

        def launcher(args):
            process = FakeProcess(len(processes) + 1)
            processes.append((tuple(args), process))
            return process

        manager = MultiDeviceMirrorManager(scrcpy="scrcpy", launcher=launcher)
        first = manager.start("phone-a", "Pixel A")
        processes[0][1].terminated = True
        restarted = manager.start("phone-a", "Pixel A")
        self.assertTrue(first.ok)
        self.assertTrue(restarted.ok)
        self.assertEqual(len(processes), 2)

        manager.start("phone-b", "Pixel B")
        self.assertEqual(manager.active_ids(), ("phone-a", "phone-b"))
        manager.stop_all()
        self.assertEqual(manager.active_ids(), ())
        self.assertTrue(all(process.terminated for _, process in processes))

    def test_stop_forces_kill_when_graceful_shutdown_times_out(self):
        process = StubbornProcess(99)
        manager = MultiDeviceMirrorManager(scrcpy="scrcpy", launcher=lambda args: process, stop_timeout=0.1)

        started = manager.start("phone-a", "Pixel A")
        stopped = manager.stop("phone-a")

        self.assertTrue(started.ok)
        self.assertFalse(stopped.ok)
        self.assertEqual(stopped.code, "TIMEOUT")
        self.assertTrue(process.killed)
        self.assertEqual(manager.active_ids(), ())
        self.assertIsNone(manager.get("phone-a"))

    def test_unavailable_scrcpy_is_explicit(self):
        manager = MultiDeviceMirrorManager(scrcpy=None, launcher=lambda args: None)
        result = manager.start("phone-a", "Pixel A")
        self.assertFalse(result.ok)
        self.assertEqual(result.code, "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
