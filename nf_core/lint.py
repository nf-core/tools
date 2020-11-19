#!/usr/bin/env python
"""Linting policy for nf-core pipeline projects.

Tests Nextflow-based pipelines to check that they adhere to
the nf-core community guidelines.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
import datetime
import fnmatch
import git
import io
import json
import logging
import os
import re
import requests
import rich
import rich.progress
import subprocess
import textwrap

import click
import requests
import yaml

import nf_core.utils
import nf_core.schema

log = logging.getLogger(__name__)

# Set up local caching for requests to speed up remote queries
nf_core.utils.setup_requests_cachedir()

# Don't pick up debug logs from the requests package
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_linting(pipeline_dir, release_mode=False, show_passed=False, md_fn=None, json_fn=None):
    """Runs all nf-core linting checks on a given Nextflow pipeline project
    in either `release` mode or `normal` mode (default). Returns an object
    of type :class:`PipelineLint` after finished.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        release_mode (bool): Set this to `True`, if the linting should be run in the `release` mode.
                             See :class:`PipelineLint` for more information.

    Returns:
        An object of type :class:`PipelineLint` that contains all the linting results.
    """

    # Create the lint object
    lint_obj = PipelineLint(pipeline_dir)

    # Run the linting tests
    try:
        lint_obj.lint_pipeline(release_mode)
    except AssertionError as e:
        log.critical("Critical error: {}".format(e))
        log.info("Stopping tests...")
        return lint_obj

    # Print the results
    lint_obj.print_results(show_passed)

    # Save results to Markdown file
    if md_fn is not None:
        log.info("Writing lint results to {}".format(md_fn))
        markdown = lint_obj.get_results_md()
        with open(md_fn, "w") as fh:
            fh.write(markdown)

    # Save results to JSON file
    if json_fn is not None:
        lint_obj.save_json_results(json_fn)

    # Exit code
    if len(lint_obj.failed) > 0:
        if release_mode:
            log.info("Reminder: Lint tests were run in --release mode.")

    return lint_obj


class PipelineLint(object):
    """Object to hold linting information and results.
    All objects attributes are set, after the :func:`PipelineLint.lint_pipeline` function was called.

    Args:
        path (str): The path to the nf-core pipeline directory.

    Attributes:
        conda_config (dict): The parsed conda configuration file content (`environment.yml`).
        conda_package_info (dict): The conda package(s) information, based on the API requests to Anaconda cloud.
        config (dict): The Nextflow pipeline configuration file content.
        dockerfile (list): A list of lines (str) from the parsed Dockerfile.
        failed (list): A list of tuples of the form: `(<error no>, <reason>)`
        files (list): A list of files found during the linting process.
        minNextflowVersion (str): The minimum required Nextflow version to run the pipeline.
        passed (list): A list of tuples of the form: `(<passed no>, <reason>)`
        path (str): Path to the pipeline directory.
        pipeline_name (str): The pipeline name, without the `nf-core` tag, for example `hlatyping`.
        release_mode (bool): `True`, if you the to linting was run in release mode, `False` else.
        warned (list): A list of tuples of the form: `(<warned no>, <reason>)`

    **Attribute specifications**

    Some of the more complex attributes of a PipelineLint object.

    * `conda_config`::

        # Example
         {
            'name': 'nf-core-hlatyping',
            'channels': ['bioconda', 'conda-forge'],
            'dependencies': ['optitype=1.3.2', 'yara=0.9.6']
         }

    * `conda_package_info`::

        # See https://api.anaconda.org/package/bioconda/bioconda-utils as an example.
         {
            <package>: <API JSON repsonse object>
         }

    * `config`: Produced by calling Nextflow with :code:`nextflow config -flat <workflow dir>`. Here is an example from
        the `nf-core/hlatyping <https://github.com/nf-core/hlatyping>`_ pipeline::

            process.container = 'nfcore/hlatyping:1.1.1'
            params.help = false
            params.outdir = './results'
            params.bam = false
            params.single_end = false
            params.seqtype = 'dna'
            params.solver = 'glpk'
            params.igenomes_base = './iGenomes'
            params.clusterOptions = false
            ...
    """

    def __init__(self, path):
        """ Initialise linting object """
        self.release_mode = False
        self.version = nf_core.__version__
        self.path = path
        self.git_sha = None
        self.files = []
        self.config = {}
        self.pipeline_name = None
        self.minNextflowVersion = None
        self.dockerfile = []
        self.conda_config = {}
        self.conda_package_info = {}
        self.schema_obj = None
        self.passed = []
        self.warned = []
        self.failed = []

        try:
            repo = git.Repo(self.path)
            self.git_sha = repo.head.object.hexsha
        except:
            pass

        # Overwrite if we have the last commit from the PR - otherwise we get a merge commit hash
        if os.environ.get("GITHUB_PR_COMMIT", "") != "":
            self.git_sha = os.environ["GITHUB_PR_COMMIT"]

    def lint_pipeline(self, release_mode=False):
        """Main linting function.

        Takes the pipeline directory as the primary input and iterates through
        the different linting checks in order. Collects any warnings or errors
        and returns summary at completion. Raises an exception if there is a
        critical error that makes the rest of the tests pointless (eg. no
        pipeline script). Results from this function are printed by the main script.

        Args:
            release_mode (boolean): Activates the release mode, which checks for
                consistent version tags of containers. Default is `False`.

        Returns:
            dict: Summary of test result messages structured as follows::

            {
                'pass': [
                    ( test-id (int), message (string) ),
                    ( test-id (int), message (string) )
                ],
                'warn': [(id, msg)],
                'fail': [(id, msg)],
            }

        Raises:
            If a critical problem is found, an ``AssertionError`` is raised.
        """
        log.info("Testing pipeline: [magenta]{}".format(self.path))
        if self.release_mode:
            log.info("Including --release mode tests")
        check_functions = [
            "check_files_exist",
            "check_licence",
            "check_docker",
            "check_nextflow_config",
            "check_actions_branch_protection",
            "check_actions_ci",
            "check_actions_lint",
            "check_actions_awstest",
            "check_actions_awsfulltest",
            "check_readme",
            "check_conda_env_yaml",
            "check_conda_dockerfile",
            "check_pipeline_todos",
            "check_pipeline_name",
            "check_cookiecutter_strings",
            "check_schema_lint",
            "check_schema_params",
        ]
        if release_mode:
            self.release_mode = True
            check_functions.extend(["check_version_consistency"])

        progress = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[func_name]}",
            transient=True,
        )
        with progress:
            lint_progress = progress.add_task(
                "Running lint checks", total=len(check_functions), func_name=check_functions[0]
            )
            for fun_name in check_functions:
                progress.update(lint_progress, advance=1, func_name=fun_name)
                log.debug("Running lint test: {}".format(fun_name))
                getattr(self, fun_name)()
                if len(self.failed) > 0:
                    log.error("Found test failures in `{}`, halting lint run.".format(fun_name))
                    break

    def check_files_exist(self):
        """Checks a given pipeline directory for required files.

        Iterates through the pipeline's directory content and checkmarks files
        for presence.
        Files that **must** be present::

            'nextflow.config',
            'nextflow_schema.json',
            ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
            'README.md',
            'CHANGELOG.md',
            'docs/README.md',
            'docs/output.md',
            'docs/usage.md',
            '.github/workflows/branch.yml',
            '.github/workflows/ci.yml',
            '.github/workflows/linting.yml'

        Files that *should* be present::

            'main.nf',
            'environment.yml',
            'Dockerfile',
            'conf/base.config',
            '.github/workflows/awstest.yml',
            '.github/workflows/awsfulltest.yml'

        Files that *must not* be present::

            'Singularity',
            'parameters.settings.json',
            'bin/markdown_to_html.r',
            '.github/workflows/push_dockerhub.yml'

        Files that *should not* be present::

            '.travis.yml'

        Raises:
            An AssertionError if neither `nextflow.config` or `main.nf` found.
        """

        # NB: Should all be files, not directories
        # List of lists. Passes if any of the files in the sublist are found.
        files_fail = [
            ["nextflow.config"],
            ["nextflow_schema.json"],
            ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md"],  # NB: British / American spelling
            ["README.md"],
            ["CHANGELOG.md"],
            [os.path.join("docs", "README.md")],
            [os.path.join("docs", "output.md")],
            [os.path.join("docs", "usage.md")],
            [os.path.join(".github", "workflows", "branch.yml")],
            [os.path.join(".github", "workflows", "ci.yml")],
            [os.path.join(".github", "workflows", "linting.yml")],
        ]
        files_warn = [
            ["main.nf"],
            ["environment.yml"],
            ["Dockerfile"],
            [os.path.join("conf", "base.config")],
            [os.path.join(".github", "workflows", "awstest.yml")],
            [os.path.join(".github", "workflows", "awsfulltest.yml")],
        ]

        # List of strings. Dails / warns if any of the strings exist.
        files_fail_ifexists = [
            "Singularity",
            "parameters.settings.json",
            os.path.join("bin", "markdown_to_html.r"),
            os.path.join(".github", "workflows", "push_dockerhub.yml"),
        ]
        files_warn_ifexists = [".travis.yml"]

        def pf(file_path):
            return os.path.join(self.path, file_path)

        # First - critical files. Check that this is actually a Nextflow pipeline
        if not os.path.isfile(pf("nextflow.config")) and not os.path.isfile(pf("main.nf")):
            self.failed.append((1, "File not found: nextflow.config or main.nf"))
            raise AssertionError("Neither nextflow.config or main.nf found! Is this a Nextflow pipeline?")

        # Files that cause an error if they don't exist
        for files in files_fail:
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(self._wrap_quotes(files))))
                self.files.extend(files)
            else:
                self.failed.append((1, "File not found: {}".format(self._wrap_quotes(files))))

        # Files that cause a warning if they don't exist
        for files in files_warn:
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(self._wrap_quotes(files))))
                self.files.extend(files)
            else:
                self.warned.append((1, "File not found: {}".format(self._wrap_quotes(files))))

        # Files that cause an error if they exist
        for file in files_fail_ifexists:
            if os.path.isfile(pf(file)):
                self.failed.append((1, "File must be removed: {}".format(self._wrap_quotes(file))))
            else:
                self.passed.append((1, "File not found check: {}".format(self._wrap_quotes(file))))

        # Files that cause a warning if they exist
        for file in files_warn_ifexists:
            if os.path.isfile(pf(file)):
                self.warned.append((1, "File should be removed: {}".format(self._wrap_quotes(file))))
            else:
                self.passed.append((1, "File not found check: {}".format(self._wrap_quotes(file))))

        # Load and parse files for later
        if "environment.yml" in self.files:
            with open(os.path.join(self.path, "environment.yml"), "r") as fh:
                self.conda_config = yaml.safe_load(fh)

    def check_docker(self):
        """Checks that Dockerfile contains the string ``FROM``."""
        if "Dockerfile" not in self.files:
            return

        fn = os.path.join(self.path, "Dockerfile")
        content = ""
        with open(fn, "r") as fh:
            content = fh.read()

        # Implicitly also checks if empty.
        if "FROM " in content:
            self.passed.append((2, "Dockerfile check passed"))
            self.dockerfile = [line.strip() for line in content.splitlines()]
            return

        self.failed.append((2, "Dockerfile check failed"))

    def check_licence(self):
        """Checks licence file is MIT.

        Currently the checkpoints are:
            * licence file must be long enough (4 or more lines)
            * licence contains the string *without restriction*
            * licence doesn't have any placeholder variables
        """
        for l in ["LICENSE", "LICENSE.md", "LICENCE", "LICENCE.md"]:
            fn = os.path.join(self.path, l)
            if os.path.isfile(fn):
                content = ""
                with open(fn, "r") as fh:
                    content = fh.read()

                # needs at least copyright, permission, notice and "as-is" lines
                nl = content.count("\n")
                if nl < 4:
                    self.failed.append((3, "Number of lines too small for a valid MIT license file: {}".format(fn)))
                    return

                # determine whether this is indeed an MIT
                # license. Most variations actually don't contain the
                # string MIT Searching for 'without restriction'
                # instead (a crutch).
                if not "without restriction" in content:
                    self.failed.append((3, "Licence file did not look like MIT: {}".format(fn)))
                    return

                # check for placeholders present in
                # - https://choosealicense.com/licenses/mit/
                # - https://opensource.org/licenses/MIT
                # - https://en.wikipedia.org/wiki/MIT_License
                placeholders = {"[year]", "[fullname]", "<YEAR>", "<COPYRIGHT HOLDER>", "<year>", "<copyright holders>"}
                if any([ph in content for ph in placeholders]):
                    self.failed.append((3, "Licence file contains placeholders: {}".format(fn)))
                    return

                self.passed.append((3, "Licence check passed"))
                return

        self.failed.append((3, "Couldn't find MIT licence file"))

    def check_nextflow_config(self):
        """Checks a given pipeline for required config variables.

        At least one string in each list must be present for fail and warn.
        Any config in config_fail_ifdefined results in a failure.

        Uses ``nextflow config -flat`` to parse pipeline ``nextflow.config``
        and print all config variables.
        NB: Does NOT parse contents of main.nf / nextflow script
        """

        # Fail tests if these are missing
        config_fail = [
            ["manifest.name"],
            ["manifest.nextflowVersion"],
            ["manifest.description"],
            ["manifest.version"],
            ["manifest.homePage"],
            ["timeline.enabled"],
            ["trace.enabled"],
            ["report.enabled"],
            ["dag.enabled"],
            ["process.cpus"],
            ["process.memory"],
            ["process.time"],
            ["params.outdir"],
            ["params.input"],
        ]
        # Throw a warning if these are missing
        config_warn = [
            ["manifest.mainScript"],
            ["timeline.file"],
            ["trace.file"],
            ["report.file"],
            ["dag.file"],
            ["process.container"],
        ]
        # Old depreciated vars - fail if present
        config_fail_ifdefined = [
            "params.version",
            "params.nf_required_version",
            "params.container",
            "params.singleEnd",
            "params.igenomesIgnore",
        ]

        # Get the nextflow config for this pipeline
        self.config = nf_core.utils.fetch_wf_config(self.path)
        for cfs in config_fail:
            for cf in cfs:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(self._wrap_quotes(cf))))
                    break
            else:
                self.failed.append((4, "Config variable not found: {}".format(self._wrap_quotes(cfs))))
        for cfs in config_warn:
            for cf in cfs:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(self._wrap_quotes(cf))))
                    break
            else:
                self.warned.append((4, "Config variable not found: {}".format(self._wrap_quotes(cfs))))
        for cf in config_fail_ifdefined:
            if cf not in self.config.keys():
                self.passed.append((4, "Config variable (correctly) not found: {}".format(self._wrap_quotes(cf))))
            else:
                self.failed.append((4, "Config variable (incorrectly) found: {}".format(self._wrap_quotes(cf))))

        # Check and warn if the process configuration is done with deprecated syntax
        process_with_deprecated_syntax = list(
            set(
                [
                    re.search(r"^(process\.\$.*?)\.+.*$", ck).group(1)
                    for ck in self.config.keys()
                    if re.match(r"^(process\.\$.*?)\.+.*$", ck)
                ]
            )
        )
        for pd in process_with_deprecated_syntax:
            self.warned.append((4, "Process configuration is done with deprecated_syntax: {}".format(pd)))

        # Check the variables that should be set to 'true'
        for k in ["timeline.enabled", "report.enabled", "trace.enabled", "dag.enabled"]:
            if self.config.get(k) == "true":
                self.passed.append((4, "Config `{}` had correct value: `{}`".format(k, self.config.get(k))))
            else:
                self.failed.append((4, "Config `{}` did not have correct value: `{}`".format(k, self.config.get(k))))

        # Check that the pipeline name starts with nf-core
        try:
            assert self.config.get("manifest.name", "").strip("'\"").startswith("nf-core/")
        except (AssertionError, IndexError):
            self.failed.append(
                (
                    4,
                    "Config `manifest.name` did not begin with `nf-core/`:\n    {}".format(
                        self.config.get("manifest.name", "").strip("'\"")
                    ),
                )
            )
        else:
            self.passed.append((4, "Config `manifest.name` began with `nf-core/`"))
            self.pipeline_name = self.config.get("manifest.name", "").strip("'").replace("nf-core/", "")

        # Check that the homePage is set to the GitHub URL
        try:
            assert self.config.get("manifest.homePage", "").strip("'\"").startswith("https://github.com/nf-core/")
        except (AssertionError, IndexError):
            self.failed.append(
                (
                    4,
                    "Config variable `manifest.homePage` did not begin with https://github.com/nf-core/:\n    {}".format(
                        self.config.get("manifest.homePage", "").strip("'\"")
                    ),
                )
            )
        else:
            self.passed.append((4, "Config variable `manifest.homePage` began with https://github.com/nf-core/"))

        # Check that the DAG filename ends in `.svg`
        if "dag.file" in self.config:
            if self.config["dag.file"].strip("'\"").endswith(".svg"):
                self.passed.append((4, "Config `dag.file` ended with `.svg`"))
            else:
                self.failed.append((4, "Config `dag.file` did not end with `.svg`"))

        # Check that the minimum nextflowVersion is set properly
        if "manifest.nextflowVersion" in self.config:
            if self.config.get("manifest.nextflowVersion", "").strip("\"'").lstrip("!").startswith(">="):
                self.passed.append((4, "Config variable `manifest.nextflowVersion` started with >= or !>="))
                # Save self.minNextflowVersion for convenience
                nextflowVersionMatch = re.search(r"[0-9\.]+(-edge)?", self.config.get("manifest.nextflowVersion", ""))
                if nextflowVersionMatch:
                    self.minNextflowVersion = nextflowVersionMatch.group(0)
                else:
                    self.minNextflowVersion = None
            else:
                self.failed.append(
                    (
                        4,
                        "Config `manifest.nextflowVersion` did not start with `>=` or `!>=` : `{}`".format(
                            self.config.get("manifest.nextflowVersion", "")
                        ).strip("\"'"),
                    )
                )

        # Check that the process.container name is pulling the version tag or :dev
        if self.config.get("process.container"):
            container_name = "{}:{}".format(
                self.config.get("manifest.name").replace("nf-core", "nfcore").strip("'"),
                self.config.get("manifest.version", "").strip("'"),
            )
            if "dev" in self.config.get("manifest.version", "") or not self.config.get("manifest.version"):
                container_name = "{}:dev".format(
                    self.config.get("manifest.name").replace("nf-core", "nfcore").strip("'")
                )
            try:
                assert self.config.get("process.container", "").strip("'") == container_name
            except AssertionError:
                if self.release_mode:
                    self.failed.append(
                        (
                            4,
                            "Config `process.container` looks wrong. Should be `{}` but is `{}`".format(
                                container_name, self.config.get("process.container", "").strip("'")
                            ),
                        )
                    )
                else:
                    self.warned.append(
                        (
                            4,
                            "Config `process.container` looks wrong. Should be `{}` but is `{}`".format(
                                container_name, self.config.get("process.container", "").strip("'")
                            ),
                        )
                    )
            else:
                self.passed.append((4, "Config `process.container` looks correct: `{}`".format(container_name)))

        # Check that the pipeline version contains `dev`
        if not self.release_mode and "manifest.version" in self.config:
            if self.config["manifest.version"].strip(" '\"").endswith("dev"):
                self.passed.append(
                    (4, "Config `manifest.version` ends in `dev`: `{}`".format(self.config["manifest.version"]))
                )
            else:
                self.warned.append(
                    (
                        4,
                        "Config `manifest.version` should end in `dev`: `{}`".format(self.config["manifest.version"]),
                    )
                )
        elif "manifest.version" in self.config:
            if "dev" in self.config["manifest.version"]:
                self.failed.append(
                    (
                        4,
                        "Config `manifest.version` should not contain `dev` for a release: `{}`".format(
                            self.config["manifest.version"]
                        ),
                    )
                )
            else:
                self.passed.append(
                    (
                        4,
                        "Config `manifest.version` does not contain `dev` for release: `{}`".format(
                            self.config["manifest.version"]
                        ),
                    )
                )

    def check_actions_branch_protection(self):
        """Checks that the GitHub Actions branch protection workflow is valid.

        Makes sure PRs can only come from nf-core dev or 'patch' of a fork.
        """
        fn = os.path.join(self.path, ".github", "workflows", "branch.yml")
        if os.path.isfile(fn):
            with open(fn, "r") as fh:
                branchwf = yaml.safe_load(fh)

            # Check that the action is turned on for PRs to master
            try:
                # Yaml 'on' parses as True - super weird
                assert "master" in branchwf[True]["pull_request_target"]["branches"]
            except (AssertionError, KeyError):
                self.failed.append(
                    (5, "GitHub Actions 'branch' workflow should be triggered for PRs to master: `{}`".format(fn))
                )
            else:
                self.passed.append(
                    (5, "GitHub Actions 'branch' workflow is triggered for PRs to master: `{}`".format(fn))
                )

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
                    self.passed.append(
                        (
                            5,
                            "GitHub Actions 'branch' workflow looks good: `{}`".format(fn),
                        )
                    )
                    break
            else:
                self.failed.append(
                    (
                        5,
                        "Couldn't find GitHub Actions 'branch' check for PRs to master: `{}`".format(fn),
                    )
                )

    def check_actions_ci(self):
        """Checks that the GitHub Actions CI workflow is valid

        Makes sure tests run with the required nextflow version.
        """
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
                self.failed.append(
                    (
                        5,
                        "GitHub Actions CI is not triggered on expected events: `{}`".format(fn),
                    )
                )
            else:
                self.passed.append((5, "GitHub Actions CI is triggered on expected events: `{}`".format(fn)))

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
                    self.failed.append(
                        (
                            5,
                            "CI is not building the correct docker image. Should be: `{}`".format(docker_build_cmd),
                        )
                    )
                else:
                    self.passed.append((5, "CI is building the correct docker image: `{}`".format(docker_build_cmd)))

                # docker pull
                docker_pull_cmd = "docker pull {}:dev".format(docker_notag)
                try:
                    steps = ciwf["jobs"]["test"]["steps"]
                    assert any([docker_pull_cmd in step["run"] for step in steps if "run" in step.keys()])
                except (AssertionError, KeyError, TypeError):
                    self.failed.append(
                        (5, "CI is not pulling the correct docker image. Should be: `{}`".format(docker_pull_cmd))
                    )
                else:
                    self.passed.append((5, "CI is pulling the correct docker image: {}".format(docker_pull_cmd)))

                # docker tag
                docker_tag_cmd = "docker tag {}:dev {}".format(docker_notag, docker_withtag)
                try:
                    steps = ciwf["jobs"]["test"]["steps"]
                    assert any([docker_tag_cmd in step["run"] for step in steps if "run" in step.keys()])
                except (AssertionError, KeyError, TypeError):
                    self.failed.append(
                        (5, "CI is not tagging docker image correctly. Should be: `{}`".format(docker_tag_cmd))
                    )
                else:
                    self.passed.append((5, "CI is tagging docker image correctly: {}".format(docker_tag_cmd)))

            # Check that we are testing the minimum nextflow version
            try:
                matrix = ciwf["jobs"]["test"]["strategy"]["matrix"]["nxf_ver"]
                assert any([self.minNextflowVersion in matrix])
            except (KeyError, TypeError):
                self.failed.append((5, "Continuous integration does not check minimum NF version: `{}`".format(fn)))
            except AssertionError:
                self.failed.append((5, "Minimum NF version different in CI and pipelines manifest: `{}`".format(fn)))
            else:
                self.passed.append((5, "Continuous integration checks minimum NF version: `{}`".format(fn)))

    def check_actions_lint(self):
        """Checks that the GitHub Actions lint workflow is valid

        Makes sure ``nf-core lint`` and ``markdownlint`` runs.
        """
        fn = os.path.join(self.path, ".github", "workflows", "linting.yml")
        if os.path.isfile(fn):
            with open(fn, "r") as fh:
                lintwf = yaml.safe_load(fh)

            # Check that the action is turned on for push and pull requests
            try:
                assert "push" in lintwf[True]
                assert "pull_request" in lintwf[True]
            except (AssertionError, KeyError, TypeError):
                self.failed.append(
                    (5, "GitHub Actions linting workflow must be triggered on PR and push: `{}`".format(fn))
                )
            else:
                self.passed.append((5, "GitHub Actions linting workflow is triggered on PR and push: `{}`".format(fn)))

            # Check that the Markdown linting runs
            Markdownlint_cmd = "markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml"
            try:
                steps = lintwf["jobs"]["Markdown"]["steps"]
                assert any([Markdownlint_cmd in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "Continuous integration must run Markdown lint Tests: `{}`".format(fn)))
            else:
                self.passed.append((5, "Continuous integration runs Markdown lint Tests: `{}`".format(fn)))

            # Check that the nf-core linting runs
            nfcore_lint_cmd = "nf-core -l lint_log.txt lint ${GITHUB_WORKSPACE}"
            try:
                steps = lintwf["jobs"]["nf-core"]["steps"]
                assert any([nfcore_lint_cmd in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "Continuous integration must run nf-core lint Tests: `{}`".format(fn)))
            else:
                self.passed.append((5, "Continuous integration runs nf-core lint Tests: `{}`".format(fn)))

    def check_actions_awstest(self):
        """Checks the GitHub Actions awstest is valid.

        Makes sure it is triggered only on ``push`` to ``master``.
        """
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
                self.failed.append(
                    (
                        5,
                        "GitHub Actions AWS test should be triggered on workflow_dispatch and not on push or PRs: `{}`".format(
                            fn
                        ),
                    )
                )
            else:
                self.passed.append((5, "GitHub Actions AWS test is triggered on workflow_dispatch: `{}`".format(fn)))

    def check_actions_awsfulltest(self):
        """Checks the GitHub Actions awsfulltest is valid.

        Makes sure it is triggered only on ``release`` and workflow_dispatch.
        """
        fn = os.path.join(self.path, ".github", "workflows", "awsfulltest.yml")
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
                self.failed.append(
                    (
                        5,
                        "GitHub Actions AWS full test should be triggered only on published release and workflow_dispatch: `{}`".format(
                            fn
                        ),
                    )
                )
            else:
                self.passed.append(
                    (
                        5,
                        "GitHub Actions AWS full test is triggered only on published release and workflow_dispatch: `{}`".format(
                            fn
                        ),
                    )
                )

            # Warn if `-profile test` is still unchanged
            try:
                steps = wf["jobs"]["run-awstest"]["steps"]
                assert any([aws_profile in step["run"] for step in steps if "run" in step.keys()])
            except (AssertionError, KeyError, TypeError):
                self.passed.append((5, "GitHub Actions AWS full test should test full datasets: `{}`".format(fn)))
            else:
                self.warned.append((5, "GitHub Actions AWS full test should test full datasets: `{}`".format(fn)))

    def check_readme(self):
        """Checks the repository README file for errors.

        Currently just checks the badges at the top of the README.
        """
        with open(os.path.join(self.path, "README.md"), "r") as fh:
            content = fh.read()

        # Check that there is a readme badge showing the minimum required version of Nextflow
        # and that it has the correct version
        nf_badge_re = r"\[!\[Nextflow\]\(https://img\.shields\.io/badge/nextflow-%E2%89%A5([\d\.]+)-brightgreen\.svg\)\]\(https://www\.nextflow\.io/\)"
        match = re.search(nf_badge_re, content)
        if match:
            nf_badge_version = match.group(1).strip("'\"")
            try:
                assert nf_badge_version == self.minNextflowVersion
            except (AssertionError, KeyError):
                self.failed.append(
                    (
                        6,
                        "README Nextflow minimum version badge does not match config. Badge: `{}`, Config: `{}`".format(
                            nf_badge_version, self.minNextflowVersion
                        ),
                    )
                )
            else:
                self.passed.append(
                    (
                        6,
                        "README Nextflow minimum version badge matched config. Badge: `{}`, Config: `{}`".format(
                            nf_badge_version, self.minNextflowVersion
                        ),
                    )
                )
        else:
            self.warned.append((6, "README did not have a Nextflow minimum version badge."))

        # Check that we have a bioconda badge if we have a bioconda environment file
        if "environment.yml" in self.files:
            bioconda_badge = "[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](https://bioconda.github.io/)"
            if bioconda_badge in content:
                self.passed.append((6, "README had a bioconda badge"))
            else:
                self.warned.append((6, "Found a bioconda environment.yml file but no badge in the README"))

    def check_version_consistency(self):
        """Checks container tags versions.

        Runs on ``process.container`` (if set) and ``$GITHUB_REF`` (if a GitHub Actions release).

        Checks that:
            * the container has a tag
            * the version numbers are numeric
            * the version numbers are the same as one-another
        """
        versions = {}
        # Get the version definitions
        # Get version from nextflow.config
        versions["manifest.version"] = self.config.get("manifest.version", "").strip(" '\"")

        # Get version from the docker slug
        if self.config.get("process.container", "") and not ":" in self.config.get("process.container", ""):
            self.failed.append(
                (
                    7,
                    "Docker slug seems not to have "
                    "a version tag: {}".format(self.config.get("process.container", "")),
                )
            )
            return

        # Get config container slugs, (if set; one container per workflow)
        if self.config.get("process.container", ""):
            versions["process.container"] = self.config.get("process.container", "").strip(" '\"").split(":")[-1]
        if self.config.get("process.container", ""):
            versions["process.container"] = self.config.get("process.container", "").strip(" '\"").split(":")[-1]

        # Get version from the GITHUB_REF env var if this is a release
        if (
            os.environ.get("GITHUB_REF", "").startswith("refs/tags/")
            and os.environ.get("GITHUB_REPOSITORY", "") != "nf-core/tools"
        ):
            versions["GITHUB_REF"] = os.path.basename(os.environ["GITHUB_REF"].strip(" '\""))

        # Check if they are all numeric
        for v_type, version in versions.items():
            if not version.replace(".", "").isdigit():
                self.failed.append((7, "{} was not numeric: {}!".format(v_type, version)))
                return

        # Check if they are consistent
        if len(set(versions.values())) != 1:
            self.failed.append(
                (
                    7,
                    "The versioning is not consistent between container, release tag "
                    "and config. Found {}".format(", ".join(["{} = {}".format(k, v) for k, v in versions.items()])),
                )
            )
            return

        self.passed.append((7, "Version tags are numeric and consistent between container, release tag and config."))

    def check_conda_env_yaml(self):
        """Checks that the conda environment file is valid.

        Checks that:
            * a name is given and is consistent with the pipeline name
            * check that dependency versions are pinned
            * dependency versions are the latest available
        """
        if "environment.yml" not in self.files:
            return

        # Check that the environment name matches the pipeline name
        pipeline_version = self.config.get("manifest.version", "").strip(" '\"")
        expected_env_name = "nf-core-{}-{}".format(self.pipeline_name.lower(), pipeline_version)
        if self.conda_config["name"] != expected_env_name:
            self.failed.append(
                (
                    8,
                    "Conda environment name is incorrect ({}, should be {})".format(
                        self.conda_config["name"], expected_env_name
                    ),
                )
            )
        else:
            self.passed.append((8, "Conda environment name was correct ({})".format(expected_env_name)))

        # Check conda dependency list
        for dep in self.conda_config.get("dependencies", []):
            if isinstance(dep, str):
                # Check that each dependency has a version number
                try:
                    assert dep.count("=") in [1, 2]
                except AssertionError:
                    self.failed.append((8, "Conda dep did not have pinned version number: `{}`".format(dep)))
                else:
                    self.passed.append((8, "Conda dep had pinned version number: `{}`".format(dep)))

                    try:
                        depname, depver = dep.split("=")[:2]
                        self.check_anaconda_package(dep)
                    except ValueError:
                        pass
                    else:
                        # Check that required version is available at all
                        if depver not in self.conda_package_info[dep].get("versions"):
                            self.failed.append((8, "Conda dep had unknown version: {}".format(dep)))
                            continue  # No need to test for latest version, continue linting
                        # Check version is latest available
                        last_ver = self.conda_package_info[dep].get("latest_version")
                        if last_ver is not None and last_ver != depver:
                            self.warned.append((8, "Conda dep outdated: `{}`, `{}` available".format(dep, last_ver)))
                        else:
                            self.passed.append((8, "Conda package is the latest available: `{}`".format(dep)))

            elif isinstance(dep, dict):
                for pip_dep in dep.get("pip", []):
                    # Check that each pip dependency has a version number
                    try:
                        assert pip_dep.count("=") == 2
                    except AssertionError:
                        self.failed.append((8, "Pip dependency did not have pinned version number: {}".format(pip_dep)))
                    else:
                        self.passed.append((8, "Pip dependency had pinned version number: {}".format(pip_dep)))

                        try:
                            pip_depname, pip_depver = pip_dep.split("==", 1)
                            self.check_pip_package(pip_dep)
                        except ValueError:
                            pass
                        else:
                            # Check, if PyPi package version is available at all
                            if pip_depver not in self.conda_package_info[pip_dep].get("releases").keys():
                                self.failed.append((8, "PyPi package had an unknown version: {}".format(pip_depver)))
                                continue  # No need to test latest version, if not available
                            last_ver = self.conda_package_info[pip_dep].get("info").get("version")
                            if last_ver is not None and last_ver != pip_depver:
                                self.warned.append(
                                    (
                                        8,
                                        "PyPi package is not latest available: {}, {} available".format(
                                            pip_depver, last_ver
                                        ),
                                    )
                                )
                            else:
                                self.passed.append((8, "PyPi package is latest available: {}".format(pip_depver)))

    def check_anaconda_package(self, dep):
        """Query conda package information.

        Sends a HTTP GET request to the Anaconda remote API.

        Args:
            dep (str): A conda package name.

        Raises:
            A ValueError, if the package name can not be resolved.
        """
        # Check if each dependency is the latest available version
        depname, depver = dep.split("=", 1)
        dep_channels = self.conda_config.get("channels", [])
        # 'defaults' isn't actually a channel name. See https://docs.anaconda.com/anaconda/user-guide/tasks/using-repositories/
        if "defaults" in dep_channels:
            dep_channels.remove("defaults")
            dep_channels.extend(["main", "anaconda", "r", "free", "archive", "anaconda-extras"])
        if "::" in depname:
            dep_channels = [depname.split("::")[0]]
            depname = depname.split("::")[1]
        for ch in dep_channels:
            anaconda_api_url = "https://api.anaconda.org/package/{}/{}".format(ch, depname)
            try:
                response = requests.get(anaconda_api_url, timeout=10)
            except (requests.exceptions.Timeout):
                self.warned.append((8, "Anaconda API timed out: {}".format(anaconda_api_url)))
                raise ValueError
            except (requests.exceptions.ConnectionError):
                self.warned.append((8, "Could not connect to Anaconda API"))
                raise ValueError
            else:
                if response.status_code == 200:
                    dep_json = response.json()
                    self.conda_package_info[dep] = dep_json
                    return
                elif response.status_code != 404:
                    self.warned.append(
                        (
                            8,
                            "Anaconda API returned unexpected response code `{}` for: {}\n{}".format(
                                response.status_code, anaconda_api_url, response
                            ),
                        )
                    )
                    raise ValueError
                elif response.status_code == 404:
                    log.debug("Could not find {} in conda channel {}".format(dep, ch))
        else:
            # We have looped through each channel and had a 404 response code on everything
            self.failed.append((8, "Could not find Conda dependency using the Anaconda API: {}".format(dep)))
            raise ValueError

    def check_pip_package(self, dep):
        """Query PyPi package information.

        Sends a HTTP GET request to the PyPi remote API.

        Args:
            dep (str): A PyPi package name.

        Raises:
            A ValueError, if the package name can not be resolved or the connection timed out.
        """
        pip_depname, pip_depver = dep.split("=", 1)
        pip_api_url = "https://pypi.python.org/pypi/{}/json".format(pip_depname)
        try:
            response = requests.get(pip_api_url, timeout=10)
        except (requests.exceptions.Timeout):
            self.warned.append((8, "PyPi API timed out: {}".format(pip_api_url)))
            raise ValueError
        except (requests.exceptions.ConnectionError):
            self.warned.append((8, "PyPi API Connection error: {}".format(pip_api_url)))
            raise ValueError
        else:
            if response.status_code == 200:
                pip_dep_json = response.json()
                self.conda_package_info[dep] = pip_dep_json
            else:
                self.failed.append((8, "Could not find pip dependency using the PyPi API: {}".format(dep)))
                raise ValueError

    def check_conda_dockerfile(self):
        """Checks the Docker build file.

        Checks that:
            * a name is given and is consistent with the pipeline name
            * dependency versions are pinned
            * dependency versions are the latest available
        """
        if "environment.yml" not in self.files or "Dockerfile" not in self.files or len(self.dockerfile) == 0:
            return

        expected_strings = [
            "COPY environment.yml /",
            "RUN conda env create --quiet -f /environment.yml && conda clean -a",
            "RUN conda env export --name {} > {}.yml".format(self.conda_config["name"], self.conda_config["name"]),
            "ENV PATH /opt/conda/envs/{}/bin:$PATH".format(self.conda_config["name"]),
        ]

        if "dev" not in self.version:
            expected_strings.append("FROM nfcore/base:{}".format(self.version))

        difference = set(expected_strings) - set(self.dockerfile)
        if not difference:
            self.passed.append((9, "Found all expected strings in Dockerfile file"))
        else:
            for missing in difference:
                self.failed.append((9, "Could not find Dockerfile file string: {}".format(missing)))

    def check_pipeline_todos(self):
        """ Go through all template files looking for the string 'TODO nf-core:' """
        ignore = [".git"]
        if os.path.isfile(os.path.join(self.path, ".gitignore")):
            with io.open(os.path.join(self.path, ".gitignore"), "rt", encoding="latin1") as fh:
                for l in fh:
                    ignore.append(os.path.basename(l.strip().rstrip("/")))
        for root, dirs, files in os.walk(self.path):
            # Ignore files
            for i in ignore:
                dirs = [d for d in dirs if not fnmatch.fnmatch(os.path.join(root, d), i)]
                files = [f for f in files if not fnmatch.fnmatch(os.path.join(root, f), i)]
            for fname in files:
                with io.open(os.path.join(root, fname), "rt", encoding="latin1") as fh:
                    for l in fh:
                        if "TODO nf-core" in l:
                            l = (
                                l.replace("<!--", "")
                                .replace("-->", "")
                                .replace("# TODO nf-core: ", "")
                                .replace("// TODO nf-core: ", "")
                                .replace("TODO nf-core: ", "")
                                .strip()
                            )
                            self.warned.append((10, "TODO string in `{}`: _{}_".format(fname, l)))

    def check_pipeline_name(self):
        """Check whether pipeline name adheres to lower case/no hyphen naming convention"""

        if self.pipeline_name.islower() and self.pipeline_name.isalnum():
            self.passed.append((12, "Name adheres to nf-core convention"))
        if not self.pipeline_name.islower():
            self.warned.append((12, "Naming does not adhere to nf-core conventions: Contains uppercase letters"))
        if not self.pipeline_name.isalnum():
            self.warned.append(
                (12, "Naming does not adhere to nf-core conventions: Contains non alphanumeric characters")
            )

    def check_cookiecutter_strings(self):
        """
        Look for the string 'cookiecutter' in all pipeline files.
        Finding it probably means that there has been a copy+paste error from the template.
        """
        try:
            # First, try to get the list of files using git
            git_ls_files = subprocess.check_output(["git", "ls-files"], cwd=self.path).splitlines()
            list_of_files = [os.path.join(self.path, s.decode("utf-8")) for s in git_ls_files]
        except subprocess.CalledProcessError as e:
            # Failed, so probably not initialised as a git repository - just a list of all files
            log.debug("Couldn't call 'git ls-files': {}".format(e))
            list_of_files = []
            for subdir, dirs, files in os.walk(self.path):
                for file in files:
                    list_of_files.append(os.path.join(subdir, file))

        # Loop through files, searching for string
        num_matches = 0
        num_files = 0
        for fn in list_of_files:
            num_files += 1
            with io.open(fn, "r", encoding="latin1") as fh:
                lnum = 0
                for l in fh:
                    lnum += 1
                    cc_matches = re.findall(r"{{\s*cookiecutter[^}]*}}", l)
                    if len(cc_matches) > 0:
                        for cc_match in cc_matches:
                            self.failed.append(
                                (13, "Found a cookiecutter template string in `{}` L{}: {}".format(fn, lnum, cc_match))
                            )
                            num_matches += 1
        if num_matches == 0:
            self.passed.append((13, "Did not find any cookiecutter template strings ({} files)".format(num_files)))

    def check_schema_lint(self):
        """ Lint the pipeline schema """

        # Only show error messages from schema
        logging.getLogger("nf_core.schema").setLevel(logging.ERROR)

        # Lint the schema
        self.schema_obj = nf_core.schema.PipelineSchema()
        self.schema_obj.get_schema_path(self.path)
        try:
            self.schema_obj.load_lint_schema()
            self.passed.append((14, "Schema lint passed"))
        except AssertionError as e:
            self.failed.append((14, "Schema lint failed: {}".format(e)))

        # Check the title and description - gives warnings instead of fail
        if self.schema_obj.schema is not None:
            try:
                self.schema_obj.validate_schema_title_description()
                self.passed.append((14, "Schema title + description lint passed"))
            except AssertionError as e:
                self.warned.append((14, e))

    def check_schema_params(self):
        """ Check that the schema describes all flat params in the pipeline """

        # First, get the top-level config options for the pipeline
        # Schema object already created in the previous test
        self.schema_obj.get_schema_path(self.path)
        self.schema_obj.get_wf_params()
        self.schema_obj.no_prompts = True

        # Remove any schema params not found in the config
        removed_params = self.schema_obj.remove_schema_notfound_configs()

        # Add schema params found in the config but not the schema
        added_params = self.schema_obj.add_schema_found_configs()

        if len(removed_params) > 0:
            for param in removed_params:
                self.warned.append((15, "Schema param `{}` not found from nextflow config".format(param)))

        if len(added_params) > 0:
            for param in added_params:
                self.failed.append(
                    (15, "Param `{}` from `nextflow config` not found in nextflow_schema.json".format(param))
                )

        if len(removed_params) == 0 and len(added_params) == 0:
            self.passed.append((15, "Schema matched params returned from nextflow config"))

    def print_results(self, show_passed=False):

        log.debug("Printing final results")
        console = Console(force_terminal=nf_core.utils.rich_force_colors())

        # Helper function to format test links nicely
        def format_result(test_results, table):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            for eid, msg in test_results:
                table.add_row(
                    Markdown("[https://nf-co.re/errors#{0}](https://nf-co.re/errors#{0}): {1}".format(eid, msg))
                )
            return table

        def _s(some_list):
            if len(some_list) > 1:
                return "s"
            return ""

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            table = Table(style="green", box=rich.box.ROUNDED)
            table.add_column(
                r"\[✔] {} Test{} Passed".format(len(self.passed), _s(self.passed)),
                no_wrap=True,
            )
            table = format_result(self.passed, table)
            console.print(table)

        # Table of warning tests
        if len(self.warned) > 0:
            table = Table(style="yellow", box=rich.box.ROUNDED)
            table.add_column(r"\[!] {} Test Warning{}".format(len(self.warned), _s(self.warned)), no_wrap=True)
            table = format_result(self.warned, table)
            console.print(table)

        # Table of failing tests
        if len(self.failed) > 0:
            table = Table(style="red", box=rich.box.ROUNDED)
            table.add_column(
                r"\[✗] {} Test{} Failed".format(len(self.failed), _s(self.failed)),
                no_wrap=True,
            )
            table = format_result(self.failed, table)
            console.print(table)

        # Summary table

        table = Table(box=rich.box.ROUNDED)
        table.add_column("[bold green]LINT RESULTS SUMMARY".format(len(self.passed)), no_wrap=True)
        table.add_row(
            r"\[✔] {:>3} Test{} Passed".format(len(self.passed), _s(self.passed)),
            style="green",
        )
        table.add_row(r"\[!] {:>3} Test Warning{}".format(len(self.warned), _s(self.warned)), style="yellow")
        table.add_row(r"\[✗] {:>3} Test{} Failed".format(len(self.failed), _s(self.failed)), style="red")
        console.print(table)

    def get_results_md(self):
        """
        Function to create a markdown file suitable for posting in a GitHub comment
        """
        # Overall header
        overall_result = "Passed :white_check_mark:"
        if len(self.failed) > 0:
            overall_result = "Failed :x:"

        # List of tests for details
        test_failure_count = ""
        test_failures = ""
        if len(self.failed) > 0:
            test_failure_count = "\n-| ❌ {:3d} tests failed       |-".format(len(self.failed))
            test_failures = "### :x: Test failures:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [Test #{0}](https://nf-co.re/errors#{0}) - {1}".format(eid, self._strip_ansi_codes(msg, "`"))
                        for eid, msg in self.failed
                    ]
                )
            )

        test_warning_count = ""
        test_warnings = ""
        if len(self.warned) > 0:
            test_warning_count = "\n!| ❗ {:3d} tests had warnings |!".format(len(self.warned))
            test_warnings = "### :heavy_exclamation_mark: Test warnings:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [Test #{0}](https://nf-co.re/errors#{0}) - {1}".format(eid, self._strip_ansi_codes(msg, "`"))
                        for eid, msg in self.warned
                    ]
                )
            )

        test_passe_count = ""
        test_passes = ""
        if len(self.passed) > 0:
            test_passed_count = "\n+| ✅ {:3d} tests passed       |+".format(len(self.passed))
            test_passes = "### :white_check_mark: Tests passed:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [Test #{0}](https://nf-co.re/errors#{0}) - {1}".format(eid, self._strip_ansi_codes(msg, "`"))
                        for eid, msg in self.passed
                    ]
                )
            )

        now = datetime.datetime.now()

        markdown = textwrap.dedent(
            """
        #### `nf-core lint` overall result: {}

        {}

        ```diff{}{}{}
        ```

        <details>

        {}{}{}### Run details:

        * nf-core/tools version {}
        * Run at `{}`

        </details>
        """
        ).format(
            overall_result,
            "Posted for pipeline commit {}".format(self.git_sha[:7]) if self.git_sha is not None else "",
            test_passed_count,
            test_warning_count,
            test_failure_count,
            test_failures,
            test_warnings,
            test_passes,
            nf_core.__version__,
            now.strftime("%Y-%m-%d %H:%M:%S"),
        )

        return markdown

    def save_json_results(self, json_fn):
        """
        Function to dump lint results to a JSON file for downstream use
        """

        log.info("Writing lint results to {}".format(json_fn))
        now = datetime.datetime.now()
        results = {
            "nf_core_tools_version": nf_core.__version__,
            "date_run": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_pass": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.passed],
            "tests_warned": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.warned],
            "tests_failed": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.failed],
            "num_tests_pass": len(self.passed),
            "num_tests_warned": len(self.warned),
            "num_tests_failed": len(self.failed),
            "has_tests_pass": len(self.passed) > 0,
            "has_tests_warned": len(self.warned) > 0,
            "has_tests_failed": len(self.failed) > 0,
            "markdown_result": self.get_results_md(),
        }
        with open(json_fn, "w") as fh:
            json.dump(results, fh, indent=4)

    def _wrap_quotes(self, files):
        if not isinstance(files, list):
            files = [files]
        bfiles = ["`{}`".format(f) for f in files]
        return " or ".join(bfiles)

    def _strip_ansi_codes(self, string, replace_with=""):
        # https://stackoverflow.com/a/14693789/713980
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub(replace_with, string)
