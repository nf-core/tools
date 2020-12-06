#!/usr/bin/env python

import os
import yaml


def actions_lint(self):
    """Checks that the GitHub Actions lint workflow is valid

    Makes sure ``nf-core lint`` and ``markdownlint`` runs.
    """
    passed = []
    warned = []
    failed = []
    fn = os.path.join(self.wf_path, ".github", "workflows", "linting.yml")
    if os.path.isfile(fn):
        with open(fn, "r") as fh:
            lintwf = yaml.safe_load(fh)

        # Check that the action is turned on for push and pull requests
        try:
            assert "push" in lintwf[True]
            assert "pull_request" in lintwf[True]
        except (AssertionError, KeyError, TypeError):
            failed.append("GitHub Actions linting workflow must be triggered on PR and push: `{}`".format(fn))
        else:
            passed.append("GitHub Actions linting workflow is triggered on PR and push: `{}`".format(fn))

        # Check that the Markdown linting runs
        Markdownlint_cmd = "markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml"
        try:
            steps = lintwf["jobs"]["Markdown"]["steps"]
            assert any([Markdownlint_cmd in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            failed.append("Continuous integration must run Markdown lint Tests: `{}`".format(fn))
        else:
            passed.append("Continuous integration runs Markdown lint Tests: `{}`".format(fn))

        # Check that the nf-core linting runs
        nfcore_lint_cmd = "nf-core -l lint_log.txt lint ${GITHUB_WORKSPACE}"
        try:
            steps = lintwf["jobs"]["nf-core"]["steps"]
            assert any([nfcore_lint_cmd in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            failed.append("Continuous integration must run nf-core lint Tests: `{}`".format(fn))
        else:
            passed.append("Continuous integration runs nf-core lint Tests: `{}`".format(fn))

    return {"passed": passed, "warned": warned, "failed": failed}
