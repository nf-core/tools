# from nf_core.pipelines.lint.rocrate_readme_sync import rocrate_readme_sync
# from pathlib import Path
import nf_core.pipelines.lint

from ..test_lint import TestLint

# import json


class TestLintROcrateReadmeSync(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self.new_pipeline = self._make_pipeline_copy()
        self.lint_obj = nf_core.pipelines.lint.PipelineLint(self._make_pipeline_copy())

    def test_rocrate_readme_sync_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.rocrate_readme_sync()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("passed", [])) > 0
