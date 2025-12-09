import subprocess
from pathlib import Path

import nf_core.subworkflows

from ...test_subworkflows import TestSubworkflows


class TestSubworkflowsLintPatch(TestSubworkflows):
    """Test linting patched subworkflows"""

    def setUp(self) -> None:
        super().setUp()

        # Install the subworkflow bam_sort_stats_samtools
        self.subworkflow_install.install("bam_sort_stats_samtools")

        # Modify the subworkflow by inserting a new input channel
        new_line = "    ch_dummy // channel: [ path ]\n"

        subworkflow_path = Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools", "main.nf")

        with open(subworkflow_path) as fh:
            lines = fh.readlines()
        for line_index in range(len(lines)):
            if "take:" in lines[line_index]:
                lines.insert(line_index + 1, new_line)
        with open(subworkflow_path, "w") as fh:
            fh.writelines(lines)

        # Create a patch file
        self.patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir)
        self.patch_obj.patch("bam_sort_stats_samtools")

    def test_lint_clean_patch(self):
        """Test linting a patched subworkflow"""

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="bam_sort_stats_samtools")

        assert len(subworkflow_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) == 1, f"Linting warned with {[x.__dict__ for x in subworkflow_lint.warned]}"
        assert any(
            [
                x.message.endswith("Can be ignored if the module is using topic channels")
                for x in subworkflow_lint.warned
            ]
        )

    def test_lint_broken_patch(self):
        """Test linting a patched subworkflow when the patch is broken"""

        # Now modify the diff
        diff_file = Path(
            self.pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools", "bam_sort_stats_samtools.diff"
        )
        subprocess.check_call(["sed", "-i''", "s/...$//", str(diff_file)])

        subworkflow_lint = nf_core.subworkflows.SubworkflowLint(directory=self.pipeline_dir)
        subworkflow_lint.lint(print_results=False, subworkflow="bam_sort_stats_samtools")

        assert len(subworkflow_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in subworkflow_lint.failed]}"
        errors = [x.message for x in subworkflow_lint.failed]
        assert "Subworkflow patch cannot be cleanly applied" in errors
        assert len(subworkflow_lint.passed) > 0
        assert len(subworkflow_lint.warned) == 1, f"Linting warned with {[x.__dict__ for x in subworkflow_lint.warned]}"
        assert any(
            [
                x.message.endswith("Can be ignored if the module is using topic channels")
                for x in subworkflow_lint.warned
            ]
        )
