#!/usr/bin/env python

import os
import yaml


def actions_awsfulltest(self):
    """Checks the GitHub Actions awsfulltest is valid.

    Makes sure it is triggered only on ``release`` and workflow_dispatch.
    """
    passed = []
    warned = []
    failed = []

    fn = os.path.join(self.wf_path, ".github", "workflows", "awsfulltest.yml")
    if os.path.isfile(fn):
        with open(fn, "r") as fh:
            wf = yaml.safe_load(fh)

        aws_profile = "-profile test "

        # Check that the action is only turned on for published releases
        try:
            assert "workflow_run" in wf[True]
            assert wf[True]["workflow_run"]["workflows"] == ["nf-core Docker push (release)"]
            assert wf[True]["workflow_run"]["types"] == ["completed"]
            assert "workflow_dispatch" in wf[True]
        except (AssertionError, KeyError, TypeError):
            failed.append("`.github/workflows/awsfulltest.yml` is not triggered correctly")
        else:
            passed.append("`.github/workflows/awsfulltest.yml` is triggered correctly")

        # Warn if `-profile test` is still unchanged
        try:
            steps = wf["jobs"]["run-awstest"]["steps"]
            assert any([aws_profile in step["run"] for step in steps if "run" in step.keys()])
        except (AssertionError, KeyError, TypeError):
            passed.append("`.github/workflows/awsfulltest.yml` does not use `-profile test`")
        else:
            warned.append("`.github/workflows/awsfulltest.yml` should test full datasets, not `-profile test`")

    return {"passed": passed, "warned": warned, "failed": failed}
