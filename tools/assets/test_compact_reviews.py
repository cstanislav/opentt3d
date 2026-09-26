"""Compaction must never select failed, incomplete or outside-build evidence."""

import json
from pathlib import Path
import tempfile
import unittest

from compact_reviews import verified_runs, generated_images, discard_images


class VerifiedReviewSelectionTests(unittest.TestCase):
    def test_retirement_records_hashes_and_preserves_sources_failures_and_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            build = root / "build-review"
            for name in ("pass", "fail", "unknown"):
                reference = build / name / "renderer3d-reference"
                reference.mkdir(parents=True)
                (reference / "model-test.pam").write_bytes(b"generated review")
                (reference / "industry-039-3.pam").write_bytes(b"original sprite")
                (reference / "industry-source-registration.png").write_bytes(b"selected comparison")
            linked = build / "pass/renderer3d-reference/model-linked.png"
            linked.symlink_to(build / "fail/renderer3d-reference/model-test.pam")
            manifest = root / "validation.json"
            manifest.write_text(json.dumps([{"output":"build-review/pass", "exit_code":0},
                                            {"output":"build-review/fail", "exit_code":1}]))
            paths = generated_images(build, verified_runs(build,[manifest]), discard=True)
            ledger = build / "retirement.json"
            self.assertEqual(discard_images(build, paths, ledger, [manifest]), len(b"generated review"))
            evidence = json.loads(ledger.read_text())
            self.assertEqual(evidence["status"],"completed")
            self.assertEqual(len(evidence["images"]),1)
            self.assertEqual(len(evidence["images"][0]["sha256"]),64)
            self.assertFalse(paths[0].exists())
            self.assertTrue(linked.is_symlink())
            for name in ("pass", "fail", "unknown"):
                reference = build / name / "renderer3d-reference"
                self.assertEqual((reference / "industry-039-3.pam").read_bytes(),b"original sprite")
                self.assertTrue((reference / "industry-source-registration.png").exists())
                if name != "pass":
                    self.assertEqual((reference / "model-test.pam").read_bytes(),b"generated review")

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
