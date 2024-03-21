import re
from pathlib import Path

import nf_core.create
import nf_core.lint


def test_nfcore_yml_pass(self):
    """Lint test: nfcore_yml - PASS"""
    self.lint_obj._load()
    results = self.lint_obj.nfcore_yml()

    assert "Repository type in `.nf-core.yml` is valid" in str(results["passed"])
    assert "nf-core version in `.nf-core.yml` is set to the latest version" in str(results["passed"])
    assert len(results.get("warned", [])) == 0
    assert len(results.get("failed", [])) == 0
    assert len(results.get("ignored", [])) == 0


def test_nfcore_yml_fail_repo_type(self):
    """Lint test: nfcore_yml - FAIL - repository type not set"""
    new_pipeline = self._make_pipeline_copy()
    nf_core_yml = Path(new_pipeline) / ".nf-core.yml"
    with open(nf_core_yml) as fh:
        content = fh.read()
        new_content = content.replace("repository_type: pipeline", "repository_type: foo")
    with open(nf_core_yml, "w") as fh:
        fh.write(new_content)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    results = lint_obj.nfcore_yml()
    assert "Repository type in `.nf-core.yml` is not valid." in str(results["failed"])
    assert len(results.get("warned", [])) == 0
    assert len(results.get("passed", [])) >= 0
    assert len(results.get("ignored", [])) == 0


def test_nfcore_yml_fail_nfcore_version(self):
    """Lint test: nfcore_yml - FAIL - nf-core version not set"""
    new_pipeline = self._make_pipeline_copy()
    nf_core_yml = Path(new_pipeline) / ".nf-core.yml"
    with open(nf_core_yml) as fh:
        content = fh.read()
        new_content = re.sub(r"nf_core_version:.+", "nf_core_version: foo", content)
    with open(nf_core_yml, "w") as fh:
        fh.write(new_content)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    results = lint_obj.nfcore_yml()
    assert "nf-core version in `.nf-core.yml` is not set to the latest version." in str(results["warned"])
    assert len(results.get("failed", [])) == 0
    assert len(results.get("passed", [])) >= 0
    assert len(results.get("ignored", [])) == 0
