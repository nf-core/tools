#!/usr/bin/env python

import os
import re
import yaml


def actions_ci(self):
    """Checks that the GitHub Actions CI workflow is valid

    Makes sure tests run with the required nextflow version.
    """
    passed = []
    warned = []
    failed = []
    fn = os.path.join(self.path, ".github", "workflows", "ci.yml")
    if os.path.isfile(fn):
        with open(fn, "r") as fh:
            ciwf = yaml.safe_load(fh)

        # Check that the action is turned on for the correct events
        try:
            expected = {"push": {"branches": ["dev"]}, "pull_request": None, "release": {"types": ["published"]}}
            # NB: YAML dict key 'on' is evaluated to a Python dict key True
            assert ciwf[True] == expected
        except (AssertionError, KeyError, TypeError):
            failed.append("GitHub Actions CI is not triggered on expected events: `{}`".format(fn))
        else:
            passed.append("GitHub Actions CI is triggered on expected events: `{}`".format(fn))

        # Check that we're pulling the right docker image and tagging it properly
        if self.config.get("process.container", ""):
            docker_notag = re.sub(r":(?:[\.\d]+|dev)$", "", self.config.get("process.container", "").strip("\"'"))
            docker_withtag = self.config.get("process.container", "").strip("\"'")

            # docker build
            docker_build_cmd = "docker build --no-cache . -t {}".format(docker_withtag)
            try:
                steps = ciwf["jobs"]["test"]["steps"]
                assert any([docker_build_cmd in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                failed.append("CI is not building the correct docker image. Should be: `{}`".format(docker_build_cmd))
            else:
                passed.append("CI is building the correct docker image: `{}`".format(docker_build_cmd))

            # docker pull
            docker_pull_cmd = "docker pull {}:dev".format(docker_notag)
            try:
                steps = ciwf["jobs"]["test"]["steps"]
                assert any([docker_pull_cmd in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                failed.append("CI is not pulling the correct docker image. Should be: `{}`".format(docker_pull_cmd))
            else:
                passed.append("CI is pulling the correct docker image: {}".format(docker_pull_cmd))

            # docker tag
            docker_tag_cmd = "docker tag {}:dev {}".format(docker_notag, docker_withtag)
            try:
                steps = ciwf["jobs"]["test"]["steps"]
                assert any([docker_tag_cmd in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                failed.append("CI is not tagging docker image correctly. Should be: `{}`".format(docker_tag_cmd))
            else:
                passed.append("CI is tagging docker image correctly: {}".format(docker_tag_cmd))

        # Check that we are testing the minimum nextflow version
        try:
            matrix = ciwf["jobs"]["test"]["strategy"]["matrix"]["nxf_ver"]
            assert any([self.minNextflowVersion in matrix])
        except (KeyError, TypeError):
            failed.append("Continuous integration does not check minimum NF version: `{}`".format(fn))
        except AssertionError:
            failed.append("Minimum NF version different in CI and pipelines manifest: `{}`".format(fn))
        else:
            passed.append("Continuous integration checks minimum NF version: `{}`".format(fn))

    return {"passed": passed, "warned": warned, "failed": failed}
