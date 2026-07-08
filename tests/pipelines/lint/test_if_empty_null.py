from pathlib import Path
from unittest import mock

import pytest
import yaml

import nf_core.pipelines.lint
from nf_core import astgrep

from ..test_lint import TestLint


class TestLintIfEmptyNull(TestLint):
    def setUp(self) -> None:
        super().setUp()
        self.new_pipeline = self._make_pipeline_copy()
        self.nf_core_yml_path = Path(self.new_pipeline) / ".nf-core.yml"
        with open(self.nf_core_yml_path) as f:
            self.nf_core_yml = yaml.safe_load(f)

    @mock.patch("nf_core.astgrep.nextflow_available", return_value=False)
    def test_if_empty_null_throws_warn(self, _mock_astgrep):
        """Tests finding ifEmpty(null) in file throws warn in linting (regex fallback)"""
        # Create a file and add examples that should fail linting
        txt_file = Path(self.new_pipeline) / "docs" / "test.txt"
        with open(txt_file, "w") as f:
            f.writelines(
                [
                    "ifEmpty(null)\n",
                    "ifEmpty (null)\n",
                    "ifEmpty( null )\n",
                    "ifEmpty ( null )\n",
                    ".ifEmpty(null)\n",
                    ". ifEmpty(null)\n",
                    "|ifEmpty(null)\n",
                    "| ifEmpty(null)\n",
                ]
            )
        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()
        result = lint_obj.pipeline_if_empty_null()
        assert len(result["warned"]) == 8

    @pytest.mark.skipif(not astgrep.nextflow_available(), reason="tree-sitter-nextflow parser not available")
    def test_if_empty_null_astgrep(self):
        """Structural matching flags real ifEmpty(null) calls but not comments"""
        nf_file = Path(self.new_pipeline) / "if_empty_test.nf"
        nf_file.write_text(
            "workflow {\n"
            "    ch_a = Channel.fromPath(params.input).ifEmpty(null)\n"
            "    ch_b = ch_a.ifEmpty( null )\n"
            "    ch_c = ch_b.ifEmpty(\n"
            "        null\n"
            "    )\n"
            "    ch_ok = ch_c.ifEmpty([])\n"
            "    // ifEmpty(null) in a comment should not be flagged\n"
            "}\n"
        )
        lint_obj = nf_core.pipelines.lint.PipelineLint(self.new_pipeline)
        lint_obj._load()
        result = lint_obj.pipeline_if_empty_null()
        warned = [w for w in result["warned"] if "if_empty_test.nf" in w]
        assert len(warned) == 3
