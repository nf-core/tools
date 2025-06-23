import nf_core.pipelines.create.create
import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintVersionConsistency(TestLint):
    def test_version_consistency(self):
        """Tests that config variable existence test fails with bad pipeline name"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()

        result = lint_obj.version_consistency()
        assert result["passed"] == [
            "Version tags are numeric and consistent between container, release tag and config."
        ]
        assert result["failed"] == ["manifest.version was not numeric: 1.0.0dev!"]

    def test_version_consistency_fail(self):
        """Tests that config variable existence test fails with bad pipeline name"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()
        # Set a bad version number
        lint_obj.nf_config["manifest.version"] = "1.0.0dev"
        lint_obj.nf_config["process.container"] = "nfcore/pipeline:latest"
        result = lint_obj.version_consistency()
        assert len(result["passed"]) == 0
        assert result["failed"] == [
            "manifest.version was not numeric: 1.0.0dev!",
            "process.container was not numeric: latest!",
            "The versioning is not consistent between container, release tag and config. Found manifest.version = 1.0.0dev, process.container = latest",
        ]
