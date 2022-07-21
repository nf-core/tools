#!/usr/bin/env python

import os
import re

import yaml


def actions_ci(self):
    """Checks that the GitHub Actions pipeline CI (Continuous Integration) workflow is valid.

    The ``.github/workflows/ci.yml`` GitHub Actions workflow runs the pipeline on a minimal test
    dataset using ``-profile test`` to check that no breaking changes have been introduced.
    Final result files are not checked, just that the pipeline exists successfully.

    This lint test checks this GitHub Actions workflow file for the following:

    * Workflow must be triggered on the following events:

      .. code-block:: yaml

         on:
             push:
             branches:
                 - dev
             pull_request:
             release:
             types: [published]

    * The minimum Nextflow version specified in the pipeline's ``nextflow.config`` matches that defined by ``nxf_ver`` in the test matrix:

      .. code-block:: yaml
         :emphasize-lines: 4

         strategy:
           matrix:
             # Nextflow versions: check pipeline minimum and current latest
             nxf_ver: ['19.10.0', '']

      .. note:: These ``matrix`` variables run the test workflow twice, varying the ``nxf_ver`` variable each time.
                This is used in the ``nextflow run`` commands to test the pipeline with both the latest available version
                of the pipeline (``''``) and the stated minimum required version.

    * The `Docker` container for the pipeline must use the correct pipeline version number:

        * Development pipelines:

          .. code-block:: bash

             docker tag nfcore/<pipeline_name>:dev nfcore/<pipeline_name>:dev

        * Released pipelines:

          .. code-block:: bash

             docker tag nfcore/<pipeline_name>:dev nfcore/<pipeline_name>:<pipeline-version>

        * Complete example for a released pipeline called *nf-core/example* with version number ``1.0.0``:

          .. code-block:: yaml
             :emphasize-lines: 3,8,9

             - name: Build new docker image
               if: env.GIT_DIFF
               run: docker build --no-cache . -t nfcore/example:1.0.0

             - name: Pull docker image
               if: ${{ !env.GIT_DIFF }}
               run: |
                 docker pull nfcore/example:dev
                 docker tag nfcore/example:dev nfcore/example:1.0.0
    """
    passed = []
    failed = []
    fn = os.path.join(self.wf_path, ".github", "workflows", "ci.yml")

    # Return an ignored status if we can't find the file
    if not os.path.isfile(fn):
        return {"ignored": ["'.github/workflows/ci.yml' not found"]}

    try:
        with open(fn, "r") as fh:
            ciwf = yaml.safe_load(fh)
    except Exception as e:
        return {"failed": [f"Could not parse yaml file: {fn}, {e}"]}

    # Check that the action is turned on for the correct events
    try:
        # NB: YAML dict key 'on' is evaluated to a Python dict key True
        if "dev" not in ciwf[True]["push"]["branches"]:
            raise AssertionError()
        pr_subtree = ciwf[True]["pull_request"]
        if not (
            pr_subtree is None
            or ("branches" in pr_subtree and "dev" in pr_subtree["branches"])
            or ("ignore_branches" in pr_subtree and not "dev" in pr_subtree["ignore_branches"])
        ):
            raise AssertionError()
        if "published" not in ciwf[True]["release"]["types"]:
            raise AssertionError()
    except (AssertionError, KeyError, TypeError):
        failed.append("'.github/workflows/ci.yml' is not triggered on expected events")
    else:
        passed.append("'.github/workflows/ci.yml' is triggered on expected events")

    # Check that we're pulling the right docker image and tagging it properly
    if self.nf_config.get("process.container", ""):
        docker_notag = re.sub(r":(?:[\.\d]+|dev)$", "", self.nf_config.get("process.container", "").strip("\"'"))
        docker_withtag = self.nf_config.get("process.container", "").strip("\"'")

        # docker build
        docker_build_cmd = f"docker build --no-cache . -t {docker_withtag}"
        try:
            steps = ciwf["jobs"]["test"]["steps"]
            if not any(docker_build_cmd in step["run"] for step in steps if "run" in step.keys()):
                raise AssertionError()
        except (AssertionError, KeyError, TypeError):
            failed.append(f"CI is not building the correct docker image. Should be: `{docker_build_cmd}`")
        else:
            passed.append(f"CI is building the correct docker image: `{docker_build_cmd}`")

        # docker pull
        docker_pull_cmd = f"docker pull {docker_notag}:dev"
        try:
            steps = ciwf["jobs"]["test"]["steps"]
            if not any(docker_pull_cmd in step["run"] for step in steps if "run" in step.keys()):
                raise AssertionError()
        except (AssertionError, KeyError, TypeError):
            failed.append(f"CI is not pulling the correct docker image. Should be: `{docker_pull_cmd}`")
        else:
            passed.append(f"CI is pulling the correct docker image: {docker_pull_cmd}")

        # docker tag
        docker_tag_cmd = f"docker tag {docker_notag}:dev {docker_withtag}"
        try:
            steps = ciwf["jobs"]["test"]["steps"]
            if not any(docker_tag_cmd in step["run"] for step in steps if "run" in step.keys()):
                raise AssertionError()
        except (AssertionError, KeyError, TypeError):
            failed.append(f"CI is not tagging docker image correctly. Should be: `{docker_tag_cmd}`")
        else:
            passed.append(f"CI is tagging docker image correctly: {docker_tag_cmd}")

    # Check that we are testing the minimum nextflow version
    try:
        nxf_ver = ciwf["jobs"]["test"]["strategy"]["matrix"]["NXF_VER"]
        if not any(i == self.minNextflowVersion for i in nxf_ver):
            raise AssertionError()
    except (KeyError, TypeError):
        failed.append("'.github/workflows/ci.yml' does not check minimum NF version")
    except AssertionError:
        failed.append(
            f"Minimum pipeline NF version '{self.minNextflowVersion}' is not tested in '.github/workflows/ci.yml'"
        )
    else:
        passed.append("'.github/workflows/ci.yml' checks minimum NF version")

    return {"passed": passed, "failed": failed}
