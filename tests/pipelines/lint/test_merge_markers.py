from pathlib import Path

import nf_core.pipelines.lint

from ..test_lint import TestLint


class TestLintMergeMarkers(TestLint):
    def test_merge_markers_found(self):
        """Missing 'jobs' field should result in failure"""
        new_pipeline = self._make_pipeline_copy()

        with open(Path(new_pipeline, "main.nf")) as fh:
            main_nf_content = fh.read()
        main_nf_content = ">>>>>>>\n" + main_nf_content
        with open(Path(new_pipeline, "main.nf"), "w") as fh:
            fh.write(main_nf_content)

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()

        results = lint_obj.merge_markers()
        assert len(results["failed"]) > 0
        assert len(results["passed"]) == 0
        assert "Merge marker '>>>>>>>' in " in results["failed"][0]

    def test_venv_is_not_scanned_for_merge_markers(self):
        """Local virtualenv dependencies are not pipeline source files."""
        new_pipeline = self._make_pipeline_copy()
        dependency_file = Path(new_pipeline, ".venv", "lib", "site-packages", "dependency.py")
        dependency_file.parent.mkdir(parents=True, exist_ok=True)
        dependency_file.write_text(">>>>>>> text in an installed dependency\\n")

        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        results = lint_obj.merge_markers()

        assert results["failed"] == []
        assert results["passed"] == ["No merge markers found in pipeline files"]
