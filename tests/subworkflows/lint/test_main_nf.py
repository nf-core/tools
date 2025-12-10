from pathlib import Path

import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows


class TestMainNf(TestSubworkflows):
    """Test main.nf functionality in subworkflows"""

    def setUp(self) -> None:
        super().setUp()

        self.subworkflow_install.install("bam_stats_samtools")
        self.main_nf = Path(
            self.pipeline_dir,
            "subworkflows",
            "nf-core",
            "bam_stats_samtools",
            "main.nf",
        )

    def test_subworkflows_lint_less_than_two_modules_warning(self):
        """Test linting a subworkflow with less than two modules"""
        # Remove two modules
        with open(self.main_nf) as fh:
            content = fh.read()
            new_content = content.replace(
                "include { SAMTOOLS_IDXSTATS } from '../../../modules/nf-core/samtools/idxstats/main'",
                "",
            )
            new_content = new_content.replace(
                "include { SAMTOOLS_FLAGSTAT } from '../../../modules/nf-core/samtools/flagstat/main'",
                "",
            )
        with open(
            self.main_nf,
            "w",
        ) as fh:
            fh.write(new_content)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
        assert len(subworkflow_lint.failed) >= 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) > 0
        assert subworkflow_lint.warned[0].lint_test == "main_nf_include"

    def test_subworkflows_lint_include_multiple_alias(self):
        """Test linting a subworkflow with multiple include methods"""
        with open(self.main_nf) as fh:
            content = fh.read()
            new_content = content.replace("SAMTOOLS_STATS", "SAMTOOLS_STATS_1")
            new_content = new_content.replace(
                "include { SAMTOOLS_STATS_1 ",
                "include { SAMTOOLS_STATS as SAMTOOLS_STATS_1; SAMTOOLS_STATS as SAMTOOLS_STATS_2 ",
            )
        with open(
            self.main_nf,
            "w",
        ) as fh:
            fh.write(new_content)

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
        assert len(subworkflow_lint.failed) >= 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) == 3
        assert any(
            [x.message == "Included component 'SAMTOOLS_STATS_1' used in main.nf" for x in subworkflow_lint.passed]
        )
        assert any(
            [x.message == "Included component 'SAMTOOLS_STATS_2' not used in main.nf" for x in subworkflow_lint.warned]
        )
        assert any(
            [
                x.message.endswith("Can be ignored if the module is using topic channels")
                for x in subworkflow_lint.warned
            ]
        )

        # cleanup
        self.subworkflow_remove.remove("bam_stats_samtools", force=True)

    def test_subworkflows_lint_capitalization_fail(self):
        """Test linting a subworkflow with a capitalization fail"""
        # change workflow name to lowercase
        with open(self.main_nf) as fh:
            content = fh.read()
            new_content = content.replace("workflow BAM_STATS_SAMTOOLS {", "workflow bam_stats_samtools {")
        with open(
            self.main_nf,
            "w",
        ) as fh:
            fh.write(new_content)
        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="bam_stats_samtools")
        assert len(subworkflow_lint.failed) >= 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) >= 0
        assert any([x.lint_test == "workflow_capitals" for x in subworkflow_lint.failed])

        # cleanup
        self.subworkflow_remove.remove("bam_stats_samtools", force=True)
