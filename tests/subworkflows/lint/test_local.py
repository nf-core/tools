import shutil
from pathlib import Path

import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows


class TestSubworkflowsLintLocal(TestSubworkflows):
    """Test linting local subworkflows"""

    def test_subworkflows_lint_local(self):
        assert self.subworkflow_install.install("fastq_align_bowtie2")
        installed = Path(self.pipeline_dir, "subworkflows", "nf-core", "fastq_align_bowtie2")
        local = Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2")
        shutil.move(installed, local)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_local_missing_files(self):
        assert self.subworkflow_install.install("fastq_align_bowtie2")
        installed = Path(self.pipeline_dir, "subworkflows", "nf-core", "fastq_align_bowtie2")
        local = Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2")
        shutil.move(installed, local)
        Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2", "meta.yml").unlink()
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
        warnings = [x.message for x in subworkflow_lint.warned]
        assert "Subworkflow `meta.yml` does not exist" in warnings

    def test_subworkflows_lint_local_old_format(self):
        assert self.subworkflow_install.install("fastq_align_bowtie2")
        installed = Path(self.pipeline_dir, "subworkflows", "nf-core", "fastq_align_bowtie2", "main.nf")
        Path(self.pipeline_dir, "subworkflows", "local").mkdir(exist_ok=True)
        local = Path(self.pipeline_dir, "subworkflows", "local", "fastq_align_bowtie2.nf")
        shutil.copy(installed, local)
        self.subworkflow_remove.remove("fastq_align_bowtie2", force=True)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, local=True)
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
