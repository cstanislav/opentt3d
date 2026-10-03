"""Manual audited publication cannot rebuild/clobber or silently skip source gates."""
import copy
import hashlib
from pathlib import Path
import unittest

from publish_reviewed_release import REPO, expected_assets, select_release, validate_draft


class ReviewedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tag,self.commit,self.run_id = "opentt3d-dev-20261003.39","a"*40,39
        self.manifest = "".join(f"{'b'*64}  {name}\n" for name in sorted(expected_assets(self.tag)-{"SHA256SUMS"})).encode()
        self.digest = hashlib.sha256(self.manifest).hexdigest()
        self.release = {"draft":True,"prerelease":True,"tag_name":self.tag,"target_commitish":self.commit,
                        "assets":[{"name":name,"size":100,"state":"uploaded","digest":"sha256:"+(self.digest if name == "SHA256SUMS" else "b"*64)} for name in expected_assets(self.tag)]}
        self.run = {"id":self.run_id,"head_sha":self.commit,"status":"completed","conclusion":"success",
                    "path":".github/workflows/opentt3d-release.yml","repository":{"full_name":REPO}}
        self.jobs = {"total_count":8,"jobs":[{"status":"completed","conclusion":"success"} for _ in range(8)]}

    def validate(self,**kwargs):
        values = dict(release=self.release,run=self.run,jobs=self.jobs,tag=self.tag,commit=self.commit,run_id=self.run_id,
                      manifest=self.manifest,manifest_sha256=self.digest)
        values.update(kwargs)
        return validate_draft(**values)

    def test_complete_exact_draft_preserves_all_nineteen_attachment_digests(self):
        self.assertEqual(len(self.validate()),19)

    def test_authenticated_paginated_lookup_finds_only_the_exact_draft(self):
        draft = {**self.release,"id":39}
        self.assertEqual(select_release([[{"id":38,"tag_name":"opentt3d-dev-20261003.38"}],[draft]],self.tag),draft)
        for pages in ([],[[{**draft,"tag_name":self.tag+"0"}]],[[draft],[draft]],[[self.release]]):
            with self.subTest(pages=pages), self.assertRaises(ValueError): select_release(pages,self.tag)

    def test_published_moved_wrong_repo_and_unfinished_runs_are_rejected(self):
        for field,value in (("draft",False),("prerelease",False),("target_commitish","main"),("tag_name",self.tag+"0")):
            changed = copy.deepcopy(self.release); changed[field] = value
            with self.subTest(release=field), self.assertRaises(ValueError): self.validate(release=changed)
        for field,value in (("id",40),("head_sha","c"*40),("conclusion","failure"),("status","in_progress"),
                            ("path",".github/workflows/unrelated.yml"),("repository",{"full_name":"other/repository"})):
            changed = copy.deepcopy(self.run); changed[field] = value
            with self.subTest(run=field), self.assertRaises(ValueError): self.validate(run=changed)

    def test_skipped_failed_or_missing_jobs_never_authorize_publication(self):
        for conclusion in ("skipped","failure",None):
            changed = copy.deepcopy(self.jobs); changed["jobs"][0]["conclusion"] = conclusion
            with self.subTest(conclusion=conclusion), self.assertRaises(ValueError): self.validate(jobs=changed)
        with self.assertRaises(ValueError): self.validate(jobs={"total_count":7,"jobs":self.jobs["jobs"][:-1]})

    def test_asset_replacement_missing_packages_and_unsealed_manifest_are_rejected(self):
        for field,value in (("digest","sha256:"+"c"*64),("size",0),("state","new")):
            changed = copy.deepcopy(self.release); changed["assets"][0][field] = value
            with self.subTest(asset=field), self.assertRaises(ValueError): self.validate(release=changed)
        changed = copy.deepcopy(self.release); changed["assets"].pop()
        with self.assertRaises(ValueError): self.validate(release=changed)
        with self.assertRaisesRegex(ValueError,"manifest has changed"): self.validate(manifest=self.manifest+b"\n")
        duplicate = self.manifest+self.manifest.splitlines(keepends=True)[0]
        with self.assertRaisesRegex(ValueError,"duplicate"): self.validate(manifest=duplicate,manifest_sha256=hashlib.sha256(duplicate).hexdigest())

    def test_workflow_only_dispatches_scoped_token_publication_and_never_repackages(self):
        root = Path(__file__).resolve().parents[2]
        workflow = (root/".github/workflows/opentt3d-publish-reviewed.yml").read_text()
        self.assertIn("workflow_dispatch:",workflow)
        self.assertIn("GH_TOKEN: ${{ github.token }}",workflow)
        self.assertIn("      actions: read",workflow)
        self.assertIn("--publish --output publication-receipt.json",workflow)
        for forbidden in ("cmake ","release upload","--clobber","release:\n","package_release.py package"):
            self.assertNotIn(forbidden,workflow)
        script = (root/"tools/opentt3d/publish_reviewed_release.py").read_text()
        self.assertIn('json.dumps({"draft":False})',script)
        self.assertIn("if args.publish:",script)
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"',script)
        self.assertIn('os.environ.get("GITHUB_REPOSITORY") != REPO',script)
        self.assertNotIn('api(f"releases/tags/',script)
        self.assertNotIn("--clobber",script)


if __name__ == "__main__":
    unittest.main()
