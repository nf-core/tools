#!/usr/bin/env python

import os
import yaml


def actions_awstest(self):
    """Checks the GitHub Actions awstest is valid.

    Makes sure it is triggered only on ``push`` to ``master``.
    """
    fn = os.path.join(self.wf_path, ".github", "workflows", "awstest.yml")
    if not os.path.isfile(fn):
        return {"ignored": ["'awstest.yml' workflow not found: `{}`".format(fn)]}

    with open(fn, "r") as fh:
        wf = yaml.safe_load(fh)

    # Check that the action is only turned on for workflow_dispatch
    try:
        assert "workflow_dispatch" in wf[True]
        assert "push" not in wf[True]
        assert "pull_request" not in wf[True]
    except (AssertionError, KeyError, TypeError):
        return {"failed": ["'.github/workflows/awstest.yml' is not triggered correctly"]}
    else:
        return {"passed": ["'.github/workflows/awstest.yml' is triggered correctly"]}
