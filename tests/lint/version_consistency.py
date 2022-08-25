import nf_core.create
import nf_core.lint


def test_version_consistency(self):
    """Tests that config variable existence test fails with bad pipeline name"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    lint_obj.nextflow_config()

    result = lint_obj.version_consistency()
    assert result["passed"] == ["Version tags are numeric and consistent between container, release tag and config."]
    assert result["failed"] == ["manifest.version was not numeric: 1.0dev!"]
