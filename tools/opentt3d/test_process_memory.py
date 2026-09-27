"""Exercise the memory guard against an actual allocating child process."""

import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from process_memory import MemoryMonitor


class LinuxMemoryExitTests(unittest.TestCase):
    def test_exit_races_preserve_the_last_valid_sample_and_peak(self):
        for terminal in ("Name:\tgame\nState:\tZ (zombie)\nThreads:\t1\n",
                         "Name:\tgame\nState:\tX (dead)\nThreads:\t1\n", FileNotFoundError()):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as directory:
                with patch("process_memory.platform.system", return_value="Linux"):
                    monitor = MemoryMonitor(directory, 64)
                try:
                    with patch.object(Path, "read_text", return_value="State:\tR (running)\nVmRSS:\t1024 kB\nVmSwap:\t256 kB\n"):
                        monitor.sample(123)
                    with patch.object(Path, "read_text", **({"side_effect": terminal} if isinstance(terminal, Exception) else {"return_value": terminal})):
                        with self.assertRaises(ProcessLookupError):
                            monitor.sample(123)
                finally:
                    monitor.close()
                report = json.loads((Path(directory) / "memory-summary.json").read_text())
                self.assertEqual(report["samples"], 1, "An exited process must not add a fabricated zero-memory sample")
                self.assertEqual(report["peak_sampled_bytes"], 1280 * 1024)
                self.assertFalse(report["limit_exceeded"])
                self.assertEqual(len((Path(directory) / "memory.jsonl").read_text().splitlines()), 1)

    def test_live_process_without_memory_fields_is_not_accepted_as_an_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("process_memory.platform.system", return_value="Linux"):
                monitor = MemoryMonitor(directory, 64)
            try:
                with patch.object(Path, "read_text", return_value="State:\tR (running)\nThreads:\t1\n"):
                    with self.assertRaisesRegex(RuntimeError, "VmRSS missing"):
                        monitor.sample(123)
                self.assertEqual(monitor.samples, 0)
            finally:
                monitor.close()


@unittest.skipUnless(platform.system() in ("Darwin", "Linux"), "native memory sampler")
class MemoryMonitorTests(unittest.TestCase):
    def test_live_child_crosses_budget_and_preserves_report(self):
        child = subprocess.Popen([sys.executable, "-u", "-c",
                                  "import time; data = bytearray(96 * 1048576); data[::4096] = b'x' * (len(data) // 4096); print('ready'); time.sleep(30)"],
                                 stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), "ready")
            with tempfile.TemporaryDirectory() as directory:
                monitor = MemoryMonitor(directory, 64)
                try:
                    with self.assertRaisesRegex(RuntimeError, "exceeds.*limit"):
                        monitor.sample(child.pid)
                finally:
                    monitor.close()
                report = json.loads((Path(directory) / "memory-summary.json").read_text())
                self.assertTrue(report["limit_exceeded"])
                self.assertGreater(report["peak_sampled_bytes"], report["limit_bytes"])
                sample = json.loads((Path(directory) / "memory.jsonl").read_text())
                self.assertEqual(sample["pid"], child.pid)
                self.assertGreater(sample["rss_bytes"], 0)
        finally:
            child.terminate()
            child.wait(timeout=10)
            child.stdout.close()


if __name__ == "__main__":
    unittest.main()
