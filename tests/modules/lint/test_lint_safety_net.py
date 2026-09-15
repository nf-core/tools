"""Regression tests for the general lint safety net (nf-core/tools#4447).

These confirm that _any_ exception raised from within a single lint test - not just the
specific known bugs fixed elsewhere - is converted into a failed lint result instead of
aborting the whole lint run, and that other components in the same batch are unaffected.
"""

from unittest.mock import patch

import nf_core.modules.lint
import nf_core.subworkflows.lint

from ...test_modules import TestModules
from ...test_subworkflows import TestSubworkflows


class TestModuleLintSafetyNet(TestModules):
    """Test that ModuleLint.lint_module isolates exceptions raised by individual lint tests"""

    def test_unexpected_exception_in_single_test_becomes_failed_result(self):
        """A lint test that raises an arbitrary exception must not abort linting"""
        self.mods_install.install("trimgalore")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)

        with patch.object(nf_core.modules.lint.ModuleLint, "module_todos", side_effect=RuntimeError("boom")):
            module_lint.lint(print_results=False, module="trimgalore")

        failed_tests = [f.lint_test for f in module_lint.failed]
        assert "module_todos" in failed_tests, f"Expected a module_todos failure, got {failed_tests}"
        assert any("boom" in f.message for f in module_lint.failed if f.lint_test == "module_todos")

    def test_exception_in_one_module_does_not_abort_batch(self):
        """Linting multiple modules at once (like --all) must not lose results for
        unaffected modules when one module's lint test raises"""
        self.mods_install.install("trimgalore")
        self.mods_install.install("tabix/tabix")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)

        def flaky_module_todos(self, module):
            if module.component_name == "trimgalore":
                raise RuntimeError("boom")

        with patch.object(nf_core.modules.lint.ModuleLint, "module_todos", flaky_module_todos):
            module_lint.lint(print_results=False, all_modules=True)

        trimgalore_failed = [f for f in module_lint.failed if f.component_name == "trimgalore"]
        assert any(f.lint_test == "module_todos" for f in trimgalore_failed)

        # tabix/tabix must still have been linted and produced results
        assert any(r.component_name == "tabix/tabix" for r in module_lint.passed), (
            "Expected tabix/tabix to still be linted despite trimgalore's module_todos raising"
        )
        assert not any(r.component_name == "tabix/tabix" and r.lint_test == "module_todos" for r in module_lint.failed)

    def test_safe_parse_component_contains_arbitrary_exception(self):
        """An unexpected exception while parsing main.nf (inputs/outputs/topics) must not
        abort linting, and must be reported as a failed result"""
        self.mods_install.install("trimgalore")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)

        with patch(
            "nf_core.components.nfcore_component.NFCoreComponent.get_outputs_from_main_nf",
            side_effect=RuntimeError("parse boom"),
        ):
            module_lint.lint(print_results=False, module="trimgalore")

        assert any(f.lint_test == "main_nf_parseable" for f in module_lint.failed), (
            f"Expected a main_nf_parseable failure, got {[f.lint_test for f in module_lint.failed]}"
        )
        assert any("parse boom" in f.message for f in module_lint.failed if f.lint_test == "main_nf_parseable")


class TestSubworkflowLintSafetyNet(TestSubworkflows):
    """Test that SubworkflowLint.lint_subworkflow isolates exceptions raised by individual lint tests"""

    def test_unexpected_exception_in_single_test_becomes_failed_result(self):
        """A lint test that raises an arbitrary exception must not abort linting"""
        self.subworkflow_install.install("bam_sort_stats_samtools")
        subworkflow_lint = nf_core.subworkflows.lint.SubworkflowLint(directory=self.pipeline_dir)

        with patch.object(
            nf_core.subworkflows.lint.SubworkflowLint, "subworkflow_todos", side_effect=RuntimeError("boom")
        ):
            subworkflow_lint.lint(print_results=False, subworkflow="bam_sort_stats_samtools")

        failed_tests = [f.lint_test for f in subworkflow_lint.failed]
        assert "subworkflow_todos" in failed_tests, f"Expected a subworkflow_todos failure, got {failed_tests}"
        assert any("boom" in f.message for f in subworkflow_lint.failed if f.lint_test == "subworkflow_todos")
