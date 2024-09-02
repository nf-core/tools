from pathlib import Path

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintFilesExist(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self.new_pipeline = self._make_pipeline_copy()

    def test_files_exist_missing_config(self):
        """Lint test: critical files missing FAIL"""

        Path(self.new_pipeline, "CHANGELOG.md").unlink()

        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()
        lint_obj.nf_config["manifest.name"] = "nf-core/testpipeline"

        results = lint_obj.files_exist()
        assert "File not found: `CHANGELOG.md`" in results["failed"]

    def test_files_exist_missing_main(self):
        """Check if missing main issues warning"""

        Path(self.new_pipeline, "main.nf").unlink()

        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()

        results = lint_obj.files_exist()
        assert "File not found: `main.nf`" in results["warned"]

    def test_files_exist_deprecated_file(self):
        """Check whether deprecated file issues warning"""

        nf = Path(self.new_pipeline, "parameters.settings.json")
        nf.touch()

        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()

        results = lint_obj.files_exist()
        assert results["failed"] == ["File must be removed: `parameters.settings.json`"]

    def test_files_exist_pass(self):
        """Lint check should pass if all files are there"""

        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()

        results = lint_obj.files_exist()
        assert results["failed"] == []

    def test_files_exist_pass_conditional_nfschema(self):
        # replace nf-validation with nf-schema in nextflow.config
        with open(Path(self.new_pipeline, "nextflow.config")) as f:
            config = f.read()
        config = config.replace("nf-validation", "nf-schema")
        with open(Path(self.new_pipeline, "nextflow.config"), "w") as f:
            f.write(config)

        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()
        lint_obj.nf_config["manifest.schema"] = "nf-core"
        results = lint_obj.files_exist()
        assert results["failed"] == []
        assert results["ignored"] == []
