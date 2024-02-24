import os

import yaml

import nf_core.lint


def test_actions_ci_pass(self):
    """Lint test: actions_ci - PASS"""
    self.lint_obj._load()
    results = self.lint_obj.actions_ci()
    assert results["passed"] == [
        "'.github/workflows/ci.yml' is triggered on expected events",
        "'.github/workflows/ci.yml' checks minimum NF version",
    ]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("failed", [])) == 0
    assert len(results.get("ignored", [])) == 0


def test_actions_ci_fail_wrong_nf(self):
    """Lint test: actions_ci - FAIL - wrong minimum version of Nextflow tested"""
    self.lint_obj._load()
    self.lint_obj.minNextflowVersion = "1.2.3"
    results = self.lint_obj.actions_ci()
    assert results["failed"] == ["Minimum pipeline NF version '1.2.3' is not tested in '.github/workflows/ci.yml'"]


def test_actions_ci_fail_wrong_trigger(self):
    """Lint test: actions_actions_ci - FAIL - workflow triggered incorrectly, NF ver not checked at all"""

    # Edit .github/workflows/actions_ci.yml to mess stuff up!
    new_pipeline = self._make_pipeline_copy()
    with open(os.path.join(new_pipeline, ".github", "workflows", "ci.yml")) as fh:
        ci_yml = yaml.safe_load(fh)
    ci_yml[True]["push"] = ["dev", "patch"]
    ci_yml["jobs"]["test"]["strategy"]["matrix"] = {"nxf_versionnn": ["foo", ""]}
    with open(os.path.join(new_pipeline, ".github", "workflows", "ci.yml"), "w") as fh:
        yaml.dump(ci_yml, fh)

    # Make lint object
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_ci()
    assert results["failed"] == [
        "'.github/workflows/ci.yml' is not triggered on expected events",
        "'.github/workflows/ci.yml' does not check minimum NF version",
    ]
