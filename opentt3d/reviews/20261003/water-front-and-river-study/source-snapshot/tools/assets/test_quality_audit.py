import json
import hashlib
import csv
from pathlib import Path
import tempfile
import unittest

from quality_audit import audit, fingerprint, original_object_layer_model, original_water_rows, write_ratings_csv, REVIEW_CHECKS
from original_water import catalogue as water_catalogue


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

    def test_ordinary_object_bindings_never_promote_source_instances_or_replace_flat_ground(self):
        tile = {"object_id":2,"kind":"statue","size_stage":None,"part":0,"ground":{"sprite":1420},"body":[{"sprite":2632}]}
        self.catalogue["bindings"] = {"objects":{"2":{"0":"sample"}}}
        scope = {key:[] for key in ("vehicles","houses","trees","industry_tiles","airport_tiles","depots","ship_depots","docks","effect_types","effect_source_frames")}
        scope.update(voxel_bindings=self.catalogue["bindings"],original_objects={"tiles":[tile],"types":[{"id":2,"climates":["temperate"]}]})
        self.review(8)
        report = audit(self.catalogue,self.reviews,self.root,scope)
        rows = {row["model"]:row for row in report["models"]}
        self.assertEqual(rows["sample"]["score"],8)
        body = rows["original/object/2/0/0/body0/climate0"]
        self.assertEqual(body["score"],5,"Model approval cannot establish an instance's original source/owner/state fidelity")
        self.assertEqual(body["owners"],["objects/2/0"])
        self.assertEqual(rows["original/object/2/0/0/ground0/climate0"]["score"],4)
        self.assertFalse(report["meets_objective"])
        self.catalogue["models"]["sample"]["origin"] = [1,0,0]
        updated = audit(self.catalogue,self.reviews,self.root,scope)
        self.assertNotEqual(body["fingerprint"],next(row for row in updated["models"] if row["model"] == body["model"])["fingerprint"])

    def test_partial_hq_never_counts_one_body_or_ground_as_complete_coverage(self):
        tiles = [{"object_id":4,"kind":"headquarters","size_stage":2,"part":part,"ground":{"sprite":2600+part},
                  "body":[{"sprite":2610+part}] if part < 3 else []} for part in range(4)]
        objects = {"tiles":tiles}
        self.catalogue["bindings"] = {"objects":{str(12+part):{"0":"sample"} for part in range(3)},
                                      "object_ground":{str(12+part):{"0":"sample"} for part in range(3)}}
        self.assertIsNone(original_object_layer_model(self.catalogue,objects,tiles[0],"body",0,0))
        self.assertIsNone(original_object_layer_model(self.catalogue,objects,tiles[0],"ground",0,0))
        self.catalogue["bindings"]["object_ground"]["15"] = {"0":"sample"}
        self.assertEqual(original_object_layer_model(self.catalogue,objects,tiles[0],"body",0,0),"sample")
        self.assertEqual(original_object_layer_model(self.catalogue,objects,tiles[3],"ground",0,0),"sample")
        self.assertIsNone(original_object_layer_model(self.catalogue,objects,tiles[0],"body",0,1))
        del self.catalogue["bindings"]["objects"]["14"]
        self.assertIsNone(original_object_layer_model(self.catalogue,objects,tiles[0],"ground",0,0))

    def test_water_scope_keeps_each_independent_owner_and_unresolved_conditional_bank(self):
        water = water_catalogue()
        rows = original_water_rows(water,{"renderer.cpp":"a"*64})
        self.assertEqual(len(rows),544)
        self.assertEqual(sum(row["model"].startswith("missing/lock/") for row in rows),192)
        self.assertEqual(sum(row["model"].startswith("original/lock/") for row in rows),96)
        self.assertEqual(sum(row["model"].startswith("original/water-slope/") for row in rows),16)
        self.assertEqual(sum(row["model"].startswith("unresolved/river-bank/") for row in rows),240)
        self.assertTrue(all(row["required_runtime_review"] and row["score"] < 8 and not row["checks"] for row in rows))
        self.assertTrue(all("intentionally absent" in row["notes"][0] for row in rows if row["model"].startswith("unresolved/")))

    def test_water_source_fingerprints_follow_originals_not_unrelated_renderer_diagnostics(self):
        import copy
        water = water_catalogue()
        first = {row["model"]:row for row in original_water_rows(water,{"renderer.cpp":"a"*64})}
        second = {row["model"]:row for row in original_water_rows(water,{"renderer.cpp":"b"*64})}
        self.assertEqual(first.keys(),second.keys())
        for name in first:
            if first[name]["representation"] == "native-water-layer":
                self.assertNotEqual(first[name]["fingerprint"],second[name]["fingerprint"])
            else:
                self.assertEqual(first[name]["fingerprint"],second[name]["fingerprint"])
        changed = copy.deepcopy(water)
        changed["locks"][0]["body"][0]["origin"][0] += 1
        updated = {row["model"]:row for row in original_water_rows(changed,{"renderer.cpp":"a"*64})}
        self.assertNotEqual(first["missing/lock/elevation0/part0/direction0/face0/climate0"]["fingerprint"],
                            updated["missing/lock/elevation0/part0/direction0/face0/climate0"]["fingerprint"])

    def test_incomplete_duplicate_or_coerced_water_scope_cannot_hide_original_states(self):
        import copy
        water = water_catalogue()
        for section in ("locks","default_water_slopes","river_edge_source_offsets"):
            for duplicate in (False,True):
                changed = copy.deepcopy(water)
                if duplicate:
                    changed[section][-1] = changed[section][0]
                else:
                    changed[section].pop()
                with self.assertRaises(ValueError):
                    original_water_rows(changed,{})
        for field in ("part","direction"):
            changed = copy.deepcopy(water)
            changed["locks"][0][field] = True
            with self.assertRaises(ValueError):
                original_water_rows(changed,{})

    def test_missing_water_scope_is_explicit_and_present_scope_cannot_inherit_model_approval(self):
        scope = {key:[] for key in ("vehicles","houses","trees","industry_tiles","airport_tiles","depots","ship_depots","docks","effect_types","effect_source_frames")}
        scope.update(voxel_bindings=self.catalogue["bindings"],original_objects={"tiles":[],"types":[]})
        without = audit(self.catalogue,self.reviews,self.root,scope)
        self.assertIn("original water-state inventory",{gap["family"] for gap in without["coverage_gaps"]})
        scope["water_structures"] = water_catalogue()
        self.review(8)
        report = audit(self.catalogue,self.reviews,self.root,scope)
        self.assertEqual(report["runtime_scope"]["water_structures"],scope["water_structures"])
        self.assertEqual(len([row for row in report["models"] if row["model"].startswith("missing/lock/")]),192)
        self.assertFalse(report["meets_objective"])
        water = next(row for row in report["models"] if row["model"].startswith("missing/lock/"))
        self.reviews["models"][water["model"]] = dict(self.reviews["models"]["sample"],fingerprint=water["fingerprint"])
        with self.assertRaisesRegex(ValueError,"Missing structural coverage"):
            audit(self.catalogue,self.reviews,self.root,scope)


if __name__ == "__main__":
    unittest.main()
