#!/usr/bin/env python
import nf_core.lint
import os
import yaml


def test_actions_branch_protection_pass(self):
    """Lint test: actions_branch_protection - PASS"""
    self.lint_obj._load()
    results = self.lint_obj.actions_branch_protection()
    assert results["passed"] == [
        "GitHub Actions 'branch.yml' workflow is triggered for PRs to master",
        "GitHub Actions 'branch.yml' workflow looks good",
    ]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("failed", [])) == 0
    assert len(results.get("ignored", [])) == 0


def test_actions_branch_protection_fail(self):
    """Lint test: actions_branch_protection - FAIL"""

    # Edit .github/workflows/branch.yml and mess stuff up!
    new_pipeline = self._make_pipeline_copy()
    with open(os.path.join(new_pipeline, ".github", "workflows", "branch.yml"), "r") as fh:
        branch_yml = yaml.safe_load(fh)
    branch_yml[True] = {"push": ["dev"]}
    branch_yml["jobs"]["test"]["steps"] = []
    with open(os.path.join(new_pipeline, ".github", "workflows", "branch.yml"), "w") as fh:
        yaml.dump(branch_yml, fh)

    # Make lint object
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_branch_protection()
    print(results["failed"])
    assert results["failed"] == [
        "GitHub Actions 'branch.yml' workflow should be triggered for PRs to master",
        "Couldn't find GitHub Actions 'branch.yml' check for PRs to master",
    ]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("passed", [])) == 0
    assert len(results.get("ignored", [])) == 0


def test_actions_branch_protection_ignore(self):
    """Lint test: actions_branch_protection - IGNORE"""

    # Delete .github/workflows/branch.yml
    new_pipeline = self._make_pipeline_copy()
    branch_fn = os.path.join(new_pipeline, ".github", "workflows", "branch.yml")
    os.remove(branch_fn)

    # Make lint object
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    lint_obj._load()
    results = lint_obj.actions_branch_protection()
    assert results["ignored"] == ["Could not find branch.yml workflow: {}".format(branch_fn)]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("passed", [])) == 0
    assert len(results.get("failed", [])) == 0
