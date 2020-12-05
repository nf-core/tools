#!/usr/bin/env python

import os
import yaml


def actions_awstest(self):
    """Checks the GitHub Actions awstest is valid.

    Makes sure it is triggered only on ``push`` to ``master``.
    """
    passed = []
    warned = []
    failed = []

    fn = os.path.join(self.path, ".github", "workflows", "awstest.yml")
    if os.path.isfile(fn):
        with open(fn, "r") as fh:
            wf = yaml.safe_load(fh)

        # Check that the action is only turned on for workflow_dispatch
        try:
            assert "workflow_dispatch" in wf[True]
            assert "push" not in wf[True]
            assert "pull_request" not in wf[True]
        except (AssertionError, KeyError, TypeError):
            failed.append(
                "GitHub Actions AWS test should be triggered on workflow_dispatch and not on push or PRs: `{}`".format(
                    fn
                )
            )
        else:
            passed.append("GitHub Actions AWS test is triggered on workflow_dispatch: `{}`".format(fn))

    return {"passed": passed, "warned": warned, "failed": failed}
