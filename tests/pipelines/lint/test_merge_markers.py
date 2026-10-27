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


    def test_pixi_environment_is_not_scanned(self):
        """Merge markers in the local Pixi environment are not project code."""
        new_pipeline = self._make_pipeline_copy()
        pixi_file = Path(new_pipeline, ".pixi", "envs", "default", "test.txt")
        pixi_file.parent.mkdir(parents=True)
        pixi_file.write_text(">>>>>>> not a project conflict")
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)
        lint_obj._load()
        assert lint_obj.merge_markers()["failed"] == []
        assert lint_obj.pipeline_todos()["warned"] == []
