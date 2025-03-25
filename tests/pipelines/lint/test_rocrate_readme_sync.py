from pathlib import Path

from ..test_lint import TestLint


class TestLintROcrateReadmeSync(TestLint):
    def test_rocrate_readme_sync_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) > 0

    def test_empty_rocrate_json(self):
        self.lint_obj._load()

        json_path = Path(self.lint_obj.wf_path, "ro-crate-metadata.json")
        with open(json_path, "w") as f:
            f.write("{}")

        assert self.lint_obj.rocrate_readme_sync()
