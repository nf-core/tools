import pytest
import shutil
import tempfile
import os

import nf_core.lint


def test_files_unchanged_pass(self):
    self.lint_obj._load()
    results = self.lint_obj.files_unchanged()
    assert len(results.get("warned", [])) == 0
    assert len(results.get("failed", [])) == 0
    assert len(results.get("ignored", [])) == 0
    assert not results.get("could_fix", True)


def test_files_unchanged_fail(self):
    failing_file = os.path.join(".github", "CONTRIBUTING.md")
    new_pipeline = self._make_pipeline_copy()
    with open(os.path.join(new_pipeline, failing_file), "a") as fh:
        fh.write("THIS SHOULD NOT BE HERE")

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    results = lint_obj.files_unchanged()
    assert len(results["failed"]) > 0
    assert failing_file in results["failed"][0]
    assert results["could_fix"]
