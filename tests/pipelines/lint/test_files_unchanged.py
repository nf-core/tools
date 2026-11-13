from pathlib import Path
from unittest import mock

import yaml

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintFilesUnchanged(TestLint):
    def test_files_unchanged_pass(self):
        self.lint_obj._load()
        # The comparison template is rendered without building an RO-Crate (which needs network access)
        with mock.patch("nf_core.pipelines.create.create.ROCrate") as mock_rocrate:
            results = self.lint_obj.files_unchanged()
        mock_rocrate.assert_not_called()
        assert len(results.get("warned", [])) == 0
        assert len(results.get("failed", [])) == 0
        assert len(results.get("ignored", [])) == 0
        assert not results.get("could_fix", True)

    def test_files_unchanged_fail(self):
        failing_file = Path("CODE_OF_CONDUCT.md")
        new_pipeline = self._make_pipeline_copy()
        with open(Path(new_pipeline, failing_file), "a") as fh:
            fh.write("THIS SHOULD NOT BE HERE")

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        results = lint_obj.files_unchanged()
        assert len(results["failed"]) > 0
        assert str(failing_file) in results["failed"][0]
        assert results["could_fix"]

    def test_files_unchanged_respects_skip_features(self):
        """The comparison copy is rendered with the pipeline's skip_features"""
        new_pipeline = self._make_pipeline_copy()
        config_fn = Path(new_pipeline, ".nf-core.yml")
        config = yaml.safe_load(config_fn.read_text())
        config["template"]["skip_features"] = ["rocrate"]
        config_fn.write_text(yaml.safe_dump(config))
        # Without rocrate, the template's .prettierignore has no ro-crate entry
        prettierignore = Path(new_pipeline, ".prettierignore")
        prettierignore.write_text(prettierignore.read_text().replace("ro-crate-metadata.json\n", ""))

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        results = lint_obj.files_unchanged()
        assert len(results.get("failed", [])) == 0
