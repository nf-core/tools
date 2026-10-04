from pathlib import Path

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintFilesUnchanged(TestLint):
    def test_files_unchanged_pass(self):
        self.lint_obj._load()
        results = self.lint_obj.files_unchanged()
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

    def test_files_unchanged_contributors_without_names(self):
        """Contributors without a name and no author should skip the test instead of crashing"""
        new_pipeline = self._make_pipeline_copy()
        config_path = Path(new_pipeline, "nextflow.config")
        config = config_path.read_text().replace("name: 'me',", "")
        config_path.write_text(config)

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        assert lint_obj.nf_config["manifest"]["contributors"]
        assert not any(c.get("name") for c in lint_obj.nf_config["manifest"]["contributors"])
        assert "author" not in lint_obj.nf_config["manifest"]

        results = lint_obj.files_unchanged()
        assert len(results["ignored"]) == 1
        assert "no names" in results["ignored"][0]
        assert "passed" not in results
        assert "failed" not in results

    def test_files_unchanged_contributors_without_names_uses_author(self):
        """Contributors without a name should fall back to manifest.author"""
        new_pipeline = self._make_pipeline_copy()
        config_path = Path(new_pipeline, "nextflow.config")
        config = config_path.read_text().replace("name: 'me',", "")
        config = config.replace("manifest {", "manifest {\n    author = 'Test Author'")
        config_path.write_text(config)

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        assert lint_obj.nf_config["manifest"]["contributors"]
        assert not any(c.get("name") for c in lint_obj.nf_config["manifest"]["contributors"])
        assert lint_obj.nf_config["manifest"]["author"] == "Test Author"

        results = lint_obj.files_unchanged()
        assert not any("no names" in msg for msg in results["ignored"])
        assert len(results["passed"]) > 0
