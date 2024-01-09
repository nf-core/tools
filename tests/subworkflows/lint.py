from pathlib import Path

import pytest

import nf_core.subworkflows

from ..utils import GITLAB_SUBWORKFLOWS_BRANCH, GITLAB_URL


def test_subworkflows_lint(self):
    """Test linting the fastq_align_bowtie2 subworkflow"""
    self.subworkflow_install.install("fastq_align_bowtie2")
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir)
    subworkflow_lint.lint(print_results=False, subworkflow="fastq_align_bowtie2")
    assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_empty(self):
    """Test linting a pipeline with no subworkflows installed"""
    with pytest.raises(LookupError):
        nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir)


def test_subworkflows_lint_new_subworkflow(self):
    """lint a new subworkflow"""
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.nfcore_modules)
    subworkflow_lint.lint(print_results=True, all_subworkflows=True)
    assert len(subworkflow_lint.failed) == 0

    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_no_gitlab(self):
    """Test linting a pipeline with no subworkflows installed"""
    with pytest.raises(LookupError):
        nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)


def test_subworkflows_lint_gitlab_subworkflows(self):
    """Lint subworkflows from a different remote"""
    self.subworkflow_install_gitlab.install("bam_stats_samtools")
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(
        dir=self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
    )
    subworkflow_lint.lint(print_results=False, all_subworkflows=True)
    assert len(subworkflow_lint.failed) == 0
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_multiple_remotes(self):
    """Lint subworkflows from a different remote"""
    self.subworkflow_install_gitlab.install("bam_stats_samtools")
    self.subworkflow_install.install("fastq_align_bowtie2")
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(
        dir=self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
    )
    subworkflow_lint.lint(print_results=False, all_subworkflows=True)
    assert len(subworkflow_lint.failed) == 0
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_snapshot_file(self):
    """Test linting a subworkflow with a snapshot file"""
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.nfcore_modules)
    subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
    assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_snapshot_file_missing_fail(self):
    """Test linting a subworkflow with a snapshot file missing, which should fail"""
    Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test.snap").unlink()
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.nfcore_modules)
    subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
    Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test.snap").touch()
    assert len(subworkflow_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0


def test_subworkflows_lint_snapshot_file_not_needed(self):
    """Test linting a subworkflow which doesn't need a snapshot file by removing the snapshot keyword in the main.nf.test file"""
    with open(Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test")) as fh:
        content = fh.read()
        new_content = content.replace("snapshot(", "snap (")
    with open(
        Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test"), "w"
    ) as fh:
        fh.write(new_content)

    Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test.snap").unlink()
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.nfcore_modules)
    subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
    Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test.snap").touch()
    assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0
