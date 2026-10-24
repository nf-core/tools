"""Isolated merge-marker lint regression without the Nextflow test fixture."""

from types import SimpleNamespace

from nf_core.pipelines.lint.merge_markers import merge_markers


def test_venv_ignored_without_hiding_actual_pipeline_conflicts(tmp_path):
    dependency = tmp_path / ".venv" / "lib" / "site-packages" / "dependency.py"
    dependency.parent.mkdir(parents=True)
    dependency.write_text(("<" * 7) + " external code\n")
    workflow = tmp_path / "main.nf"
    workflow.write_text("workflow { log.info 'clean' }\n")
    lint = SimpleNamespace(wf_path=tmp_path, lint_config={})

    result = merge_markers(lint)
    assert result["failed"] == []
    assert result["passed"] == ["No merge markers found in pipeline files"]

    workflow.write_text((">" * 7) + " pipeline code\n")
    result = merge_markers(lint)
    assert len(result["failed"]) == 1
    assert "main.nf" in result["failed"][0]
    assert ".venv" not in result["failed"][0]
