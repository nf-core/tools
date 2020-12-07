#!/usr/bin/env python

import os
import yaml
import nf_core.lint


def test_actions_ci_pass(self):
    """Lint test: actions_ci - PASS"""
    self.lint_obj._load()
    results = self.lint_obj.actions_ci()
    assert results["passed"] == [
        "'.github/workflows/ci.yml' is triggered on expected events",
        "CI is building the correct docker image: `docker build --no-cache . -t nfcore/testpipeline:dev`",
        "CI is pulling the correct docker image: docker pull nfcore/testpipeline:dev",
        "CI is tagging docker image correctly: docker tag nfcore/testpipeline:dev nfcore/testpipeline:dev",
        "'.github/workflows/ci.yml' checks minimum NF version",
    ]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("failed", [])) == 0
    assert len(results.get("ignored", [])) == 0


def test_actions_ci_fail(self):
    """Lint test: actions_actions_ci - FAIL"""

    # Edit .github/workflows/actions_ci.yml to mess stuff up!
    new_pipeline = self._make_pipeline_copy()
    with open(os.path.join(new_pipeline, ".github", "workflows", "ci.yml"), "r") as fh:
        ci_yml = yaml.safe_load(fh)
    ci_yml[True]["push"] = ["dev", "patch"]
    ci_yml["jobs"]["test"]["strategy"]["matrix"]["nxf_ver"] = ["foo", ""]
    ci_yml["jobs"]["test"]["steps"] = [{"name": "Check out pipeline code", "uses": "actions/checkout@v2"}]
    with open(os.path.join(new_pipeline, ".github", "workflows", "ci.yml"), "w") as fh:
        yaml.dump(ci_yml, fh)

    # Make lint object
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_ci()
    assert results["failed"] == [
        "'.github/workflows/ci.yml' is not triggered on expected events",
        "CI is not building the correct docker image. Should be: `docker build --no-cache . -t nfcore/testpipeline:dev`",
        "CI is not pulling the correct docker image. Should be: `docker pull nfcore/testpipeline:dev`",
        "CI is not tagging docker image correctly. Should be: `docker tag nfcore/testpipeline:dev nfcore/testpipeline:dev`",
        "Minimum NF version in '.github/workflows/ci.yml' different to pipeline's manifest"
    ]
    assert len(results.get("warned", [])) == 0
    assert len(results.get("passed", [])) == 0
    assert len(results.get("ignored", [])) == 0
