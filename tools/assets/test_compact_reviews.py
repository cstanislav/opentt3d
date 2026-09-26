"""Compaction must never select failed, incomplete or outside-build evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from compact_reviews import verified_runs


class VerifiedReviewSelectionTests(unittest.TestCase):
    def test_failures_override_success_and_resolved_paths_stay_inside_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            build = root / "build-review"
            build.mkdir()
            (build / "outside").symlink_to(root / "external")
            (build / "alias").symlink_to(build / "linked-run")
            first, second = root / "first.json", root / "second.json"
            first.write_text(json.dumps([
                {"output":"build-review/pass", "exit_code":0},
                {"output":"build-review/conflict", "exit_code":0},
                {"output":"build-review/fail", "exit_code":1},
                {"output":"build-review/outside", "exit_code":0},
                {"output":"build-review/../external", "exit_code":0},
                {"output":"build-review/alias", "exit_code":0},
            ]))
            second.write_text(json.dumps([{"output":str(build / "conflict"), "exit_code":1}]))
            self.assertEqual(verified_runs(build, [first, second]), [build / "pass"])
            self.assertEqual(verified_runs(build, [second, first]), [build / "pass"])
            self.assertEqual(verified_runs(build, []), [])

    def test_incomplete_and_noninteger_outcomes_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            manifest = root / "runs.json"
            for records in ({}, [{"output":"build-review/run"}],
                            [{"output":"build-review/run", "exit_code":False}],
                            [{"output":"build-review/run", "exit_code":"0"}]):
                manifest.write_text(json.dumps(records))
                with self.subTest(records=records), self.assertRaises(ValueError):
                    verified_runs(root / "build-review", [manifest])


if __name__ == "__main__":
    unittest.main()
