import shutil
from pathlib import Path

import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows


class TestSubworkflowsLintLocal(TestSubworkflows):
    """Test linting local subworkflows"""

    def setUp(self) -> None:
        super().setUp()
        assert self.subworkflow_install.install("fastq_align_bowtie2")
        self.install_path = Path(self.pipeline_dir, "subworkflows", "nf-core", "fastq_align_bowtie2")
        self.local_path = Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2")

    def test_subworkflows_lint_local(self):
        shutil.move(self.install_path, self.local_path)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_local_missing_files(self):
        shutil.move(self.install_path, self.local_path)
        Path(self.local_path, "meta.yml").unlink()
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
        warnings = [x.message for x in subworkflow_lint.warned]
        assert "Subworkflow `meta.yml` does not exist" in warnings

    def test_subworkflows_lint_local_old_format(self):
        Path(self.pipeline_dir, "subworkflows", "local").mkdir(exist_ok=True)
        local = Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2.nf")
        shutil.copy(Path(self.install_path, "main.nf"), local)
        self.subworkflow_remove.remove("fastq_align_bowtie2", force=True)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
