#!/usr/bin/env python

import os
import yaml


def actions_branch_protection(self):
    """Checks that the GitHub Actions branch protection workflow is valid.

    Makes sure PRs can only come from nf-core dev or 'patch' of a fork.
    """
    passed = []
    warned = []
    failed = []
    fn = os.path.join(self.wf_path, ".github", "workflows", "branch.yml")
    if os.path.isfile(fn):
        with open(fn, "r") as fh:
            branchwf = yaml.safe_load(fh)

        # Check that the action is turned on for PRs to master
        try:
            # Yaml 'on' parses as True - super weird
            assert "master" in branchwf[True]["pull_request_target"]["branches"]
        except (AssertionError, KeyError):
            failed.append("GitHub Actions 'branch' workflow should be triggered for PRs to master: `{}`".format(fn))
        else:
            passed.append("GitHub Actions 'branch' workflow is triggered for PRs to master: `{}`".format(fn))

        # Check that PRs are only ok if coming from an nf-core `dev` branch or a fork `patch` branch
        steps = branchwf.get("jobs", {}).get("test", {}).get("steps", [])
        for step in steps:
            has_name = step.get("name", "").strip() == "Check PRs"
            has_if = step.get("if", "").strip() == "github.repository == 'nf-core/{}'".format(
                self.pipeline_name.lower()
            )
            # Don't use .format() as the squiggly brackets get ridiculous
            has_run = step.get(
                "run", ""
            ).strip() == '{ [[ ${{github.event.pull_request.head.repo.full_name}} == nf-core/PIPELINENAME ]] && [[ $GITHUB_HEAD_REF = "dev" ]]; } || [[ $GITHUB_HEAD_REF == "patch" ]]'.replace(
                "PIPELINENAME", self.pipeline_name.lower()
            )
            if has_name and has_if and has_run:
                passed.append("GitHub Actions 'branch' workflow looks good: `{}`".format(fn))
                break
        else:
            failed.append("Couldn't find GitHub Actions 'branch' check for PRs to master: `{}`".format(fn))
    return {"passed": passed, "warned": warned, "failed": failed}
