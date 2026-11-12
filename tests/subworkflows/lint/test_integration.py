import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows
from ...utils import GITLAB_SUBWORKFLOWS_BRANCH, GITLAB_URL


class TestSubworkflowsLintIntegration(TestSubworkflows):
    """Test general subworkflow linting functionality"""

    def test_subworkflows_lint(self):
        """Test linting the fastq_align_bowtie2 subworkflow"""
        self.subworkflow_install.install("fastq_align_bowtie2")
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="fastq_align_bowtie2")
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_empty(self):
        """Test linting a pipeline with no subworkflows installed"""
        self.subworkflow_remove.remove("utils_nextflow_pipeline", force=True)
        self.subworkflow_remove.remove("utils_nfcore_pipeline", force=True)
        self.subworkflow_remove.remove("utils_nfschema_plugin", force=True)
        nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        assert "No subworkflows from https://github.com/nf-core/modules.git installed in pipeline" in self.caplog.text

    def test_subworkflows_lint_new_subworkflow(self):
        """lint a new subworkflow"""
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules)
        subworkflow_lint.lint(print_results=True, all_subworkflows=True)
        assert len(subworkflow_lint.failed) == 0
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_no_gitlab(self):
        """Test linting a pipeline with no subworkflows installed"""
        nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        assert f"No subworkflows from {GITLAB_URL} installed in pipeline" in self.caplog.text

    def test_subworkflows_lint_gitlab_subworkflows(self):
        """Lint subworkflows from a different remote"""
        self.subworkflow_install_gitlab.install("bam_stats_samtools")
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(
            directory=self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
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
            directory=self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
        )
        subworkflow_lint.lint(print_results=False, all_subworkflows=True)
        assert len(subworkflow_lint.failed) == 0
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0

    def test_subworkflows_lint_fix(self):
        """update the meta.yml of a subworkflow"""
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.nfcore_modules, fix=True)
        subworkflow_lint.lint(print_results=False, subworkflow="test_subworkflow")
        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
