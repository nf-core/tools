import json
from pathlib import Path

from ..test_lint import TestLint


class TestLintROcrateReadmeSync(TestLint):
    def test_rocrate_readme_sync_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) > 0

    def test_rocrate_readme_sync_fail(self):
        self.lint_obj._load()

        json_path = Path(self.lint_obj.wf_path, "ro-crate-metadata.json")
        with open(json_path) as f:
            try:
                rocrate = json.load(f)
            except json.JSONDecodeError as e:
                raise UserWarning(f"Unable to load JSON file '{json_path}' due to error {e}")
        rocrate["@graph"][0]["description"] = "This is a test script"
        with open(json_path, "w") as f:
            json.dump(rocrate, f, indent=4)
        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("failed", [])) == 1
        assert (
            "The RO-Crate descriptions do not match the README.md content. Use `nf-core lint --fix rocrate_readme_sync` to update."
            in results.get("failed", [])
        )

    def test_rocrate_readme_sync_fixed(self):
        self.lint_obj._load()
        json_path = Path(self.lint_obj.wf_path, "ro-crate-metadata.json")
        with open(json_path) as f:
            try:
                rocrate = json.load(f)
            except json.JSONDecodeError as e:
                raise UserWarning(f"Unable to load JSON file '{json_path}' due to error {e}")
        rocrate["@graph"][0]["description"] = "This is a test script"
        with open(json_path, "w") as f:
            json.dump(rocrate, f, indent=4)

        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("failed", [])) == 1

        # Fix the issue
        assert "rocrate_readme_sync" in self.lint_obj.lint_tests
        self.lint_obj.fix = ["rocrate_readme_sync"]
        self.lint_obj._load()
        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("failed", [])) == 0
