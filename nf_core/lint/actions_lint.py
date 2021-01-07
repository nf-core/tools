#!/usr/bin/env python

import os
import yaml


def actions_lint(self):
    """Checks that the GitHub Actions *linting* workflow is valid.

    This linting test checks that the GitHub Actions ``.github/workflows/linting.yml`` workflow
    correctly runs the ``nf-core lint``, ``markdownlint`` and ``yamllint`` commands.
    These three commands all check code syntax and code-style.
    Yes that's right - this is a lint test that checks that lint tests are running. Meta.

    This lint test checks this GitHub Actions workflow file for the following:

    * That the workflow is triggered on the  ``push`` and ``pull_request`` events, eg:

      .. code-block:: yaml

         on:
             push:
             pull_request:

    * That the workflow has a step that runs ``nf-core lint``, eg:


      .. code-block:: yaml

         jobs:
           nf-core:
             steps:
               - run: nf-core -l lint_log.txt lint ${GITHUB_WORKSPACE} --markdown lint_results.md

    * That the workflow has a step that runs ``markdownlint``, eg:


      .. code-block:: yaml

         jobs:
           Markdown:
             steps:
               - run: markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml

    * That the workflow has a step that runs ``yamllint``, eg:


      .. code-block:: yaml

         jobs:
           YAML:
             steps:
               - run: yamllint $(find ${GITHUB_WORKSPACE} -type f -name "*.yml")

    .. warning::  These are minimal examples of the commands and YAML structure and are not complete
               enough to be copied into the workflow file.
    """
    passed = []
    warned = []
    failed = []
    fn = os.path.join(self.wf_path, ".github", "workflows", "linting.yml")
    if os.path.isfile(fn):
        try:
            with open(fn, "r") as fh:
                lintwf = yaml.safe_load(fh)
        except:
            return {"failed": ["Could not parse yaml file: {}".format(fn)]}

        # Check that the action is turned on for push and pull requests
        try:
            assert "push" in lintwf[True]
            assert "pull_request" in lintwf[True]
        except (AssertionError, KeyError, TypeError):
            failed.append("GitHub Actions linting workflow must be triggered on PR and push: `{}`".format(fn))
        else:
            passed.append("GitHub Actions linting workflow is triggered on PR and push: `{}`".format(fn))

        # Check that the nf-core linting runs
        nfcore_lint_cmd = "nf-core -l lint_log.txt lint ${GITHUB_WORKSPACE} --markdown lint_results.md"
        try:
            steps = lintwf["jobs"]["nf-core"]["steps"]
            assert any([nfcore_lint_cmd in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            failed.append("Continuous integration must run nf-core lint Tests: `{}`".format(fn))
        else:
            passed.append("Continuous integration runs nf-core lint Tests: `{}`".format(fn))

        # Check that the Markdown linting runs
        markdownlint_cmd = "markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml"
        try:
            steps = lintwf["jobs"]["Markdown"]["steps"]
            assert any([markdownlint_cmd in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            failed.append("Continuous integration must run Markdown lint Tests: `{}`".format(fn))
        else:
            passed.append("Continuous integration runs Markdown lint Tests: `{}`".format(fn))

        # Check that the Markdown linting runs
        yamllint_cmd = 'yamllint $(find ${GITHUB_WORKSPACE} -type f -name "*.yml")'
        try:
            steps = lintwf["jobs"]["YAML"]["steps"]
            assert any([yamllint_cmd in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            failed.append("Continuous integration must run YAML lint Tests: `{}`".format(fn))
        else:
            passed.append("Continuous integration runs YAML lint Tests: `{}`".format(fn))

    return {"passed": passed, "warned": warned, "failed": failed}
