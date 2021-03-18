#!/usr/bin/env python

import os
import yaml


def actions_awstest(self):
    """Checks the GitHub Actions awstest is valid.

    In addition to small test datasets run on GitHub Actions, we provide the possibility of testing the pipeline on AWS.
    This should ensure that the pipeline runs as expected on AWS (which often has its own unique edge cases).

    .. warning:: Running tests on AWS incurs costs, so these tests are not triggered automatically.
                 Instead, they use the ``workflow_dispatch`` trigger, which allows for manual triggering
                 of the workflow when testing on AWS is desired.

    .. note::  You can trigger the tests by going to the `Actions` tab on the pipeline GitHub repository
                  and selecting the `nf-core AWS test` workflow on the left.

    The ``.github/workflows/awstest.yml`` file is tested for the following:

    * Must *not* be turned on for ``push`` or ``pull_request``.
    * Must be turned on for ``workflow_dispatch``.

    """
    fn = os.path.join(self.wf_path, ".github", "workflows", "awstest.yml")
    if not os.path.isfile(fn):
        return {"ignored": ["'awstest.yml' workflow not found: `{}`".format(fn)]}

    try:
        with open(fn, "r") as fh:
            wf = yaml.safe_load(fh)
    except Exception as e:
        return {"failed": ["Could not parse yaml file: {}, {}".format(fn, e)]}

    # Check that the action is only turned on for workflow_dispatch
    try:
        assert "workflow_dispatch" in wf[True]
        assert "push" not in wf[True]
        assert "pull_request" not in wf[True]
    except (AssertionError, KeyError, TypeError):
        return {"failed": ["'.github/workflows/awstest.yml' is not triggered correctly"]}
    else:
        return {"passed": ["'.github/workflows/awstest.yml' is triggered correctly"]}
