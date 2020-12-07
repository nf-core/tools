#!/usr/bin/env python

import os
import yaml


def actions_branch_protection(self):
    """Checks that the GitHub Actions branch protection workflow is valid.

    A common error when making pull-requests to nf-core repositories is to open the
    PR against the default branch: ``master``. This branch should only have stable
    code from the latest release, so development PRs nearly always go to ``dev`` instead.
    We want ``master`` to be the default branch so that people pull this when running workflows.

    The only time that PRs against ``master`` are allows is when they come from a branch
    on the main nf-core repo called ``dev`` or a fork with a branch called ``patch``.

    The GitHub Actions ``.github/workflows/branch.yml`` workflow checks pull requests
    opened against ``master`` to ensure that they are coming from an allowed branch
    and throws an error if not. It also posts a comment to the PR explaining the failure
    and how to resolve it.

    Specifically, the lint test checks that:

    * The workflow is triggered for the ``pull_request`` event against ``master``:

      .. code-block:: yaml

         on:
           pull_request:
             branches:
             - master

    * The code that checks PRs to the protected nf-core repo ``master`` branch can only come from an nf-core ``dev`` branch or a fork ``patch`` branch:

      .. code-block:: yaml

         steps:
           # PRs to the nf-core repo master branch are only ok if coming from the nf-core repo `dev` or any `patch` branches
           - name: Check PRs
             if: github.repository == 'nf-core/<pipeline_name>'
             run: |
               { [[ ${{github.event.pull_request.head.repo.full_name}} == nf-core/<pipeline_name> ]] && [[ $GITHUB_HEAD_REF = "dev" ]]; } || [[ $GITHUB_HEAD_REF == "patch" ]]

    .. seealso:: For branch protection in repositories outside of `nf-core`, you can add an additional step to this workflow.
                 Keep the `nf-core` branch protection step, to ensure that the ``nf-core lint`` tests pass. It should just be ignored
                 if you're working outside of `nf-core`. Here's an example of how this code could look:

                 .. code-block:: yaml

                    steps:
                      # Usual nf-core branch check, looked for by the nf-core lint test
                      - name: Check PRs
                        if: github.repository == 'nf-core/<pipeline_name>'
                        run: |
                          { [[ ${{github.event.pull_request.head.repo.full_name}} == nf-core/<pipeline_name> ]] && [[ $GITHUB_HEAD_REF = "dev" ]]; } || [[ $GITHUB_HEAD_REF == "patch" ]]

                      ##### Your custom code: Check PRs in your own repository
                      - name: Check PRs in another repository
                        if: github.repository == '<repo_name>/<pipeline_name>'
                        run: |
                          { [[ ${{github.event.pull_request.head.repo.full_name}} == <repo_name>/<pipeline_name> ]] && [[ $GITHUB_HEAD_REF = "dev" ]]; } || [[ $GITHUB_HEAD_REF == "patch" ]]
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
