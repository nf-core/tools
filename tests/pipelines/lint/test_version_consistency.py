import nf_core.pipelines.create.create
import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintVersionConsistency(TestLint):
    def test_version_consistency_pass(self):
        """Tests that pipeline version consistency test passes with good pipeline name"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()

        # Set the version numbers to be consistent
        lint_obj.nf_config["manifest.version"] = "1.0.0"
        lint_obj.nf_config["config_yml.template.version"] = "1.0.0"

        result = lint_obj.version_consistency()
        assert result["passed"] == [
            "Version tags are consistent between container, release tag, config and nf-core.yml."
        ]
        assert result["failed"] == []

    def test_version_consistency_not_numeric(self):
        """Tests that pipeline version consistency test fails with non-numeric version numbers"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()

        result = lint_obj.version_consistency()
        assert result["passed"] == [
            "Version tags are consistent between container, release tag, config and nf-core.yml."
        ]
        assert result["failed"] == ["manifest.version was not numeric: 1.0.0dev!"]

    def test_version_consistency_container_not_consistent(self):
        """Tests that pipeline version consistency test fails with inconsistent version numbers"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()

        # Set a bad version number for the container
        lint_obj.nf_config["process.container"] = "nfcore/pipeline:latest"
        # Set the version numbers to be consistent
        lint_obj.nf_config["manifest.version"] = "1.0.0"
        lint_obj.nf_config["config_yml.template.version"] = "1.0.0"

        result = lint_obj.version_consistency()
        assert len(result["passed"]) == 0
        assert result["failed"] == [
            "process.container was not numeric: latest!",
            "The versioning is not consistent between container, release tag and config. Found manifest.version = 1.0.0, process.container = latest, nfcore_yml.version = 1.0.0",
        ]

    def test_version_consistency_yml_not_consistent(self):
        """Tests that pipeline version consistency test fails with inconsistent version numbers"""
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj.load_pipeline_config()
        lint_obj.nextflow_config()

        # Set a bad version number for the YAML file
        lint_obj.nf_config["config_yml.template.version"] = "0.0.0"
        # Set the version numbers to be consistent
        lint_obj.nf_config["process.container"] = "nfcore/pipeline:1.0.0"
        lint_obj.nf_config["manifest.version"] = "1.0.0"

        result = lint_obj.version_consistency()
        assert len(result["passed"]) == 0
        assert result["failed"] == [
            "The versioning is not consistent between container, release tag and config. Found manifest.version = 1.0.0, process.container = 1.0.0, nfcore_yml.version = 0.0.0",
        ]
