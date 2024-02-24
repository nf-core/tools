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
    self.subworkflow_remove.remove("utils_nextflow_pipeline", force=True)
    self.subworkflow_remove.remove("utils_nfcore_pipeline", force=True)
    self.subworkflow_remove.remove("utils_nfvalidation_plugin", force=True)
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


def test_subworkflows_lint_less_than_two_modules_warning(self):
    """Test linting a subworkflow with less than two modules"""
    self.subworkflow_install.install("bam_stats_samtools")
    # Remove two modules
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf")) as fh:
        content = fh.read()
        new_content = content.replace(
            "include { SAMTOOLS_IDXSTATS } from '../../../modules/nf-core/samtools/idxstats/main'", ""
        )
        new_content = new_content.replace(
            "include { SAMTOOLS_FLAGSTAT } from '../../../modules/nf-core/samtools/flagstat/main'", ""
        )
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf"), "w") as fh:
        fh.write(new_content)
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir)
    subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
    assert len(subworkflow_lint.failed) >= 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) > 0
    assert subworkflow_lint.warned[0].lint_test == "main_nf_include"
    # cleanup
    self.subworkflow_remove.remove("bam_stats_samtools", force=True)


def test_subworkflows_lint_include_multiple_alias(self):
    """Test linting a subworkflow with multiple include methods"""
    self.subworkflow_install.install("bam_stats_samtools")
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf")) as fh:
        content = fh.read()
        new_content = content.replace("SAMTOOLS_STATS", "SAMTOOLS_STATS_1")
        new_content = new_content.replace(
            "include { SAMTOOLS_STATS_1 ",
            "include { SAMTOOLS_STATS as SAMTOOLS_STATS_1; SAMTOOLS_STATS as SAMTOOLS_STATS_2 ",
        )
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf"), "w") as fh:
        fh.write(new_content)

    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir)
    subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
    assert len(subworkflow_lint.failed) >= 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) == 2
    assert any(
        [
            x.message == "Included component 'SAMTOOLS_STATS_1' versions are added in main.nf"
            for x in subworkflow_lint.passed
        ]
    )
    assert any([x.message == "Included component 'SAMTOOLS_STATS_1' used in main.nf" for x in subworkflow_lint.passed])
    assert any(
        [x.message == "Included component 'SAMTOOLS_STATS_2' not used in main.nf" for x in subworkflow_lint.warned]
    )

    # cleanup
    self.subworkflow_remove.remove("bam_stats_samtools", force=True)


def test_subworkflows_lint_capitalization_fail(self):
    """Test linting a subworkflow with a capitalization fail"""
    self.subworkflow_install.install("bam_stats_samtools")
    # change workflow name to lowercase
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf")) as fh:
        content = fh.read()
        new_content = content.replace("workflow BAM_STATS_SAMTOOLS {", "workflow bam_stats_samtools {")
    with open(Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_stats_samtools", "main.nf"), "w") as fh:
        fh.write(new_content)
    subworkflow_lint = nf_core.subworkflows.SubworkflowLint(dir=self.pipeline_dir)
    subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
    assert len(subworkflow_lint.failed) >= 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
    assert len(subworkflow_lint.passed) > 0
    assert len(subworkflow_lint.warned) >= 0
    assert any([x.lint_test == "workflow_capitals" for x in subworkflow_lint.failed])

    # cleanup
    self.subworkflow_remove.remove("bam_stats_samtools", force=True)
