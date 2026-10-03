import json
import hashlib
import csv
from pathlib import Path
import tempfile
import unittest

from quality_audit import audit, fingerprint, write_ratings_csv, REVIEW_CHECKS


class QualityAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        assets = self.root/"assets/3d"
        assets.mkdir(parents=True)
        (assets/"models.json").write_text('{"models":[],"materials":{}}')
        for pack in ("houses","trees","industries","vehicles"):
            (assets/f"{pack}.json").write_text(json.dumps({"assemblies" if pack=="vehicles" else "models":{}}))
        self.model = {"size":[2,2,2],"origin":[0,0,0],"cell_size":[0.5,0.5,1],"runs":[[0,0,0,2,1]]}
        self.catalogue = {"format":1,"materials":[[2,3,4,5,6,7]],"models":{"sample":self.model},"bindings":{"houses":{"1":{"0":"sample"}}}}
        self.reviews = {"format":1,"models":{}}
        (self.root/"review.txt").write_text("Retained individual visual evidence")

    def review(self,score=8):
        entry = {"score":score,"fingerprint":fingerprint(self.model,self.catalogue["materials"]),
                 "checks":{key:True for key in REVIEW_CHECKS},"evidence":["review.txt"],
                 "evidence_sha256":{"review.txt":hashlib.sha256((self.root/"review.txt").read_bytes()).hexdigest()},
                 "notes":["Individual review"],"defects":[]}
        self.reviews["models"]["sample"] = entry
        return entry

    def test_unreviewed_models_are_scored_not_approved(self):
        report = audit(self.catalogue,self.reviews,self.root)
        self.assertEqual(report["models"][0]["score"],5)
        self.assertEqual(report["models"][0]["status"],"structural-screen-only")
        self.assertFalse(report["meets_objective"])
        self.assertGreater(len(report["coverage_gaps"]),0)

    def test_csv_retains_every_score_and_note_with_repository_lf(self):
        report = audit(self.catalogue,self.reviews,self.root)
        report["models"][0]["notes"] = ['A comma, and "quoted" source observation.']
        path = self.root/"ledger/ratings.csv"
        write_ratings_csv(path,report["models"])
        self.assertNotIn(b"\r",path.read_bytes())
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows),len(report["models"]))
        self.assertEqual(rows[0]["notes"],report["models"][0]["notes"][0])
        self.assertEqual(rows[0]["score/10"],"5")

    def test_matching_review_never_hides_remaining_families(self):
        self.review()
        report = audit(self.catalogue,self.reviews,self.root)
        self.assertEqual(report["models"][0]["score"],8)
        self.assertFalse(report["meets_objective"])

    def test_changed_faces_and_cells_invalidate_prior_score(self):
        self.review()
        for key,value in (("materials",[[2,3,4,5,6,8]]),("models",{"sample":dict(self.model,origin=[1,0,0])})):
            changed = dict(self.catalogue,**{key:value})
            report = audit(changed,self.reviews,self.root)
            self.assertEqual(report["models"][0]["score"],5)
            self.assertEqual(report["models"][0]["status"],"stale-review")

    def test_material_renumbering_preserves_the_exact_face_review(self):
        first = fingerprint(self.model,self.catalogue["materials"])
        model = dict(self.model,runs=[[0,0,0,2,2]])
        self.assertEqual(first,fingerprint(model,[[15]*6]+self.catalogue["materials"]))
        split = dict(self.model,runs=[[0,0,0,1,1],[1,0,0,1,2]])
        self.assertEqual(first,fingerprint(split,self.catalogue["materials"]*2),"Synonymous materials can split a run without changing one cell or face")

    def test_eight_requires_every_check_no_defects_and_existing_evidence(self):
        for check in REVIEW_CHECKS:
            entry = self.review()
            entry["checks"][check] = False
            with self.assertRaisesRegex(ValueError,"all six review checks"):
                audit(self.catalogue,self.reviews,self.root)
        entry = self.review()
        entry["defects"] = ["Off-center cupola"]
        with self.assertRaisesRegex(ValueError,"all six review checks"):
            audit(self.catalogue,self.reviews,self.root)
        entry = self.review()
        entry["evidence"] = ["missing.png"]
        with self.assertRaisesRegex(ValueError,"Missing individual review evidence"):
            audit(self.catalogue,self.reviews,self.root)

    def test_boolean_score_and_checks_are_not_numeric_ratings(self):
        self.review(True)
        with self.assertRaisesRegex(ValueError,"Invalid individual score"):
            audit(self.catalogue,self.reviews,self.root)
        entry = self.review()
        entry["checks"]["source"] = 1
        with self.assertRaisesRegex(ValueError,"explicit booleans"):
            audit(self.catalogue,self.reviews,self.root)

    def test_missing_or_nonlist_defects_cannot_bypass_eight(self):
        entry = self.review()
        del entry["defects"]
        with self.assertRaisesRegex(ValueError,"all six review checks"):
            audit(self.catalogue,self.reviews,self.root)
        entry["defects"] = False
        with self.assertRaisesRegex(ValueError,"explicit list"):
            audit(self.catalogue,self.reviews,self.root)

    def test_source_layer_cannot_claim_structural_eight(self):
        from quality_audit import apply_review
        entry = self.review()
        row = {"model":"sample","representation":"original-source-layer","fingerprint":entry["fingerprint"]}
        with self.assertRaisesRegex(ValueError,"Missing structural coverage"):
            apply_review(row,entry,self.root)

    def test_unknown_model_review_is_rejected(self):
        self.reviews["models"]["missing"] = {}
        with self.assertRaisesRegex(ValueError,"missing models"):
            audit(self.catalogue,self.reviews,self.root)

    def test_changed_evidence_cannot_keep_eight_and_missing_hashes_are_rejected(self):
        entry = self.review()
        (self.root/"review.txt").write_text("Different or overwritten evidence")
        report = audit(self.catalogue,self.reviews,self.root)
        self.assertEqual(report["models"][0]["score"],5)
        self.assertEqual(report["models"][0]["status"],"stale-evidence")
        entry["evidence_sha256"] = {}
        with self.assertRaisesRegex(ValueError,"immutable hashes"):
            audit(self.catalogue,self.reviews,self.root)

    def test_shared_immutable_evidence_invalidates_lower_ratings_too(self):
        entry = self.review(7)
        self.reviews["evidence_sha256"] = entry.pop("evidence_sha256")
        report = audit(self.catalogue,self.reviews,self.root)
        self.assertEqual(report["models"][0]["score"],7)
        self.assertEqual(report["models"][0]["evidence_sha256"],self.reviews["evidence_sha256"])
        (self.root/"review.txt").write_text("Changed lower-rated evidence")
        report = audit(self.catalogue,self.reviews,self.root)
        self.assertEqual(report["models"][0]["score"],5)
        self.assertEqual(report["models"][0]["status"],"stale-evidence")

    def test_scope_retains_each_missing_object_layer_and_does_not_invent_absent_bodies(self):
        scope = {key:[] for key in ("vehicles","houses","trees","industry_tiles","airport_tiles","depots","ship_depots","docks","effect_types","effect_source_frames")}
        tile = {"object_id":4,"kind":"headquarters","size_stage":0,"part":2,"ground":{"sprite":2606},"body":[]}
        scope.update(voxel_bindings=self.catalogue["bindings"],original_objects={"tiles":[tile],"types":[{"id":4,"climates":["temperate","arctic","tropic","toyland"]}]})
        report = audit(self.catalogue,self.reviews,self.root,scope)
        objects = [row for row in report["models"] if row["model"].startswith("missing/object/")]
        self.assertEqual(len(objects),4)
        self.assertTrue(all("/ground0/" in row["model"] and row["score"] == 1 for row in objects))
        self.assertEqual(report["runtime_scope"]["original_objects"]["tiles"][0]["body"],[])
        self.assertEqual(len(report["intentional_absences"]),4)
        scope["original_objects"]["types"][0]["climates"] = ["temperate"]
        restricted = audit(self.catalogue,self.reviews,self.root,scope)
        self.assertEqual(len([row for row in restricted["models"] if row["model"].startswith("missing/object/")]),1)
        scope["voxel_bindings"] = {}
        with self.assertRaisesRegex(ValueError,"exact reviewed catalogue"):
            audit(self.catalogue,self.reviews,self.root,scope)


if __name__ == "__main__":
    unittest.main()
