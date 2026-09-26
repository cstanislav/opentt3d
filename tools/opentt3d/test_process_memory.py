"""Exercise the memory guard against an actual allocating child process."""

import json
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import unittest

from process_memory import MemoryMonitor


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
