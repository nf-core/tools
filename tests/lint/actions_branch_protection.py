#!/usr/bin/env python

import os
import yaml
import nf_core.lint


def test_actions_wf_branch_pass(self):
    """Test that linting passes for correct action branch protection"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    results = lint_obj.actions_branch_protection()
    assert results["failed"] == []

def test_actions_wf_branch_fail(self):
    """Test failing wf branch protection"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    fn = os.path.join(new_pipeline, ".github", "workflows", "branch.yml")
    with open(fn, "r") as fh:
        branchwf = yaml.safe_load(fh)
    
    del branchwf[True]

    with open(fn, "w") as fh:
        yaml.dump(branchwf, fh)

    results = lint_obj.actions_branch_protection()
    assert results["failed"] == ["GitHub Actions 'branch' workflow should be triggered for PRs to master: `{}`".format(fn)]
