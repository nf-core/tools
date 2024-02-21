import os
from pathlib import Path

import nf_core.lint


def test_files_exist_missing_config(self):
    """Lint test: critical files missing FAIL"""
    new_pipeline = self._make_pipeline_copy()

    Path(new_pipeline, "CHANGELOG.md").unlink()

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    lint_obj.nf_config["manifest.name"] = "nf-core/testpipeline"

    results = lint_obj.files_exist()
    assert results["failed"] == ["File not found: `CHANGELOG.md`"]


def test_files_exist_missing_main(self):
    """Check if missing main issues warning"""
    new_pipeline = self._make_pipeline_copy()

    Path(new_pipeline, "main.nf").unlink()

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.files_exist()
    assert "File not found: `main.nf`" in results["warned"]


def test_files_exist_depreciated_file(self):
    """Check whether depreciated file issues warning"""
    new_pipeline = self._make_pipeline_copy()

    nf = Path(new_pipeline, "parameters.settings.json")
    os.system(f"touch {nf}")

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.files_exist()
    assert results["failed"] == ["File must be removed: `parameters.settings.json`"]


def test_files_exist_pass(self):
    """Lint check should pass if all files are there"""

    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.files_exist()
    assert results["failed"] == []


def test_files_exist_pass_conditional(self):
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    lint_obj.nf_config["plugins"] = []
    lib_dir = Path(new_pipeline, "lib")
    lib_dir.mkdir()
    (lib_dir / "nfcore_external_java_deps.jar").touch()
    results = lint_obj.files_exist()
    assert results["failed"] == []
    assert results["ignored"] == []


def test_files_exist_fail_conditional(self):
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    lib_dir = Path(new_pipeline, "lib")
    lib_dir.mkdir()
    (lib_dir / "nfcore_external_java_deps.jar").touch()
    results = lint_obj.files_exist()
    assert results["failed"] == ["File must be removed: `lib/nfcore_external_java_deps.jar`"]
    assert results["ignored"] == []
