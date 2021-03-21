#!/usr/bin/env python
"""Linting policy for nf-core pipeline projects.

Tests Nextflow-based pipelines to check that they adhere to
the nf-core community guidelines.
"""

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
import datetime
import git
import json
import logging
import os
import re
import rich
import rich.progress
import yaml

import nf_core.utils

log = logging.getLogger(__name__)


def run_linting(
    pipeline_dir, release_mode=False, fix=(), show_passed=False, fail_ignored=False, md_fn=None, json_fn=None
):
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
    lint_obj = PipelineLint(pipeline_dir, release_mode, fix, fail_ignored)

    # Load the various pipeline configs
    lint_obj._load_lint_config()
    lint_obj._load_pipeline_config()
    lint_obj._load_conda_environment()
    lint_obj._list_files()

    # Run the linting tests
    try:
        lint_obj._lint_pipeline()
    except AssertionError as e:
        log.critical("Critical error: {}".format(e))
        log.info("Stopping tests...")
        return lint_obj

    # Print the results
    lint_obj._print_results(show_passed)

    # Save results to Markdown file
    if md_fn is not None:
        log.info("Writing lint results to {}".format(md_fn))
        markdown = lint_obj._get_results_md()
        with open(md_fn, "w") as fh:
            fh.write(markdown)

    # Save results to JSON file
    if json_fn is not None:
        lint_obj._save_json_results(json_fn)

    # Reminder about --release mode flag if we had failures
    if len(lint_obj.failed) > 0:
        if release_mode:
            log.info("Reminder: Lint tests were run in --release mode.")

    return lint_obj


class PipelineLint(nf_core.utils.Pipeline):
    """Object to hold linting information and results.

    Inherits :class:`nf_core.utils.Pipeline` class.

    Use the :func:`PipelineLint._lint_pipeline` function to run lint tests.

    Args:
        path (str): The path to the nf-core pipeline directory.

    Attributes:
        failed (list): A list of tuples of the form: ``(<test-name>, <reason>)``
        ignored (list): A list of tuples of the form: ``(<test-name>, <reason>)``
        lint_config (dict): The parsed nf-core linting config for this pipeline
        passed (list): A list of tuples of the form: ``(<test-name>, <reason>)``
        release_mode (bool): `True`, if you the to linting was run in release mode, `False` else.
        warned (list): A list of tuples of the form: ``(<warned no>, <reason>)``
    """

    from .files_exist import files_exist
    from .files_unchanged import files_unchanged
    from .nextflow_config import nextflow_config
    from .actions_ci import actions_ci
    from .actions_awstest import actions_awstest
    from .actions_awsfulltest import actions_awsfulltest
    from .readme import readme
    from .version_consistency import version_consistency
    from .conda_env_yaml import conda_env_yaml
    from .conda_dockerfile import conda_dockerfile
    from .pipeline_todos import pipeline_todos
    from .pipeline_name_conventions import pipeline_name_conventions
    from .template_strings import template_strings
    from .schema_lint import schema_lint
    from .schema_params import schema_params
    from .actions_schema_validation import actions_schema_validation
    from .merge_markers import merge_markers

    def __init__(self, wf_path, release_mode=False, fix=(), fail_ignored=False):
        """ Initialise linting object """

        # Initialise the parent object
        super().__init__(wf_path)

        self.lint_config = {}
        self.release_mode = release_mode
        self.fail_ignored = fail_ignored
        self.failed = []
        self.ignored = []
        self.fixed = []
        self.passed = []
        self.warned = []
        self.could_fix = []
        self.lint_tests = [
            "files_exist",
            "nextflow_config",
            "files_unchanged",
            "actions_ci",
            "actions_awstest",
            "actions_awsfulltest",
            "readme",
            "conda_env_yaml",
            "conda_dockerfile",
            "pipeline_todos",
            "pipeline_name_conventions",
            "template_strings",
            "schema_lint",
            "schema_params",
            "actions_schema_validation",
            "merge_markers",
        ]
        if self.release_mode:
            self.lint_tests.extend(["version_consistency"])
        self.fix = fix
        self.progress_bar = None

    def _load(self):
        """Load information about the pipeline into the PipelineLint object"""
        # Load everything using the parent object
        super()._load()

        # Load lint object specific stuff
        self._load_lint_config()

    def _load_lint_config(self):
        """Parse a pipeline lint config file.

        Look for a file called either `.nf-core-lint.yml` or
        `.nf-core-lint.yaml` in the pipeline root directory and parse it.
        (`.yml` takes precedence).

        Add parsed config to the `self.lint_config` class attribute.
        """
        config_fn = os.path.join(self.wf_path, ".nf-core-lint.yml")

        # Pick up the file if it's .yaml instead of .yml
        if not os.path.isfile(config_fn):
            config_fn = os.path.join(self.wf_path, ".nf-core-lint.yaml")

        # Load the YAML
        try:
            with open(config_fn, "r") as fh:
                self.lint_config = yaml.safe_load(fh)
        except FileNotFoundError:
            log.debug("No lint config file found: {}".format(config_fn))

        # Check if we have any keys that don't match lint test names
        for k in self.lint_config:
            if k not in self.lint_tests:
                log.warning("Found unrecognised test name '{}' in pipeline lint config".format(k))

    def _lint_pipeline(self):
        """Main linting function.

        Takes the pipeline directory as the primary input and iterates through
        the different linting checks in order. Collects any warnings or errors
        into object attributes: ``passed``, ``ignored``, ``warned`` and ``failed``.
        """
        log.info(f"Testing pipeline: [magenta]{self.wf_path}")
        if self.release_mode:
            log.info("Including --release mode tests")

        # Check that we recognise all --fix arguments
        unrecognised_fixes = list(test for test in self.fix if test not in self.lint_tests)
        if len(unrecognised_fixes):
            raise AssertionError(
                "Unrecognised lint test{} for '--fix': '{}'".format(
                    "s" if len(unrecognised_fixes) > 1 else "", "', '".join(unrecognised_fixes)
                )
            )

        # Check that the pipeline_dir is a clean git repo
        if len(self.fix):
            log.info("Attempting to automatically fix failing tests")
            try:
                repo = git.Repo(self.wf_path)
            except git.exc.InvalidGitRepositoryError as e:
                raise AssertionError(
                    f"'{self.wf_path}' does not appear to be a git repository, this is required when running with '--fix'"
                )
            # Check that we have no uncommitted changes
            if repo.is_dirty(untracked_files=True):
                raise AssertionError(
                    "Uncommitted changes found in pipeline directory!\nPlease commit these before running with '--fix'"
                )

        self.progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with self.progress_bar:
            lint_progress = self.progress_bar.add_task(
                "Running lint checks", total=len(self.lint_tests), test_name=self.lint_tests[0]
            )
            for test_name in self.lint_tests:
                if self.lint_config.get(test_name, {}) is False:
                    log.debug("Skipping lint test '{}'".format(test_name))
                    self.ignored.append((test_name, test_name))
                    continue
                self.progress_bar.update(lint_progress, advance=1, test_name=test_name)
                log.debug("Running lint test: {}".format(test_name))
                test_results = getattr(self, test_name)()
                for test in test_results.get("passed", []):
                    self.passed.append((test_name, test))
                for test in test_results.get("ignored", []):
                    if self.fail_ignored:
                        self.failed.append((test_name, test))
                    else:
                        self.ignored.append((test_name, test))
                for test in test_results.get("fixed", []):
                    self.fixed.append((test_name, test))
                for test in test_results.get("warned", []):
                    self.warned.append((test_name, test))
                for test in test_results.get("failed", []):
                    self.failed.append((test_name, test))
                if test_results.get("could_fix", False):
                    self.could_fix.append(test_name)

    def _print_results(self, show_passed=False):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")
        console = Console(force_terminal=nf_core.utils.rich_force_colors())

        # Helper function to format test links nicely
        def format_result(test_results, table):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            for eid, msg in test_results:
                table.add_row(Markdown("[{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html): {1}".format(eid, msg)))
            return table

        def _s(some_list):
            if len(some_list) != 1:
                return "s"
            return ""

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            table = Table(style="green", box=rich.box.ROUNDED)
            table.add_column(r"[✔] {} Test{} Passed".format(len(self.passed), _s(self.passed)), no_wrap=True)
            table = format_result(self.passed, table)
            console.print(table)

        # Table of fixed tests
        if len(self.fixed) > 0:
            table = Table(style="bright_blue", box=rich.box.ROUNDED)
            table.add_column(r"[?] {} Test{} Fixed".format(len(self.fixed), _s(self.fixed)), no_wrap=True)
            table = format_result(self.fixed, table)
            console.print(table)

        # Table of ignored tests
        if len(self.ignored) > 0:
            table = Table(style="grey58", box=rich.box.ROUNDED)
            table.add_column(r"[?] {} Test{} Ignored".format(len(self.ignored), _s(self.ignored)), no_wrap=True)
            table = format_result(self.ignored, table)
            console.print(table)

        # Table of warning tests
        if len(self.warned) > 0:
            table = Table(style="yellow", box=rich.box.ROUNDED)
            table.add_column(r"[!] {} Test Warning{}".format(len(self.warned), _s(self.warned)), no_wrap=True)
            table = format_result(self.warned, table)
            console.print(table)

        # Table of failing tests
        if len(self.failed) > 0:
            table = Table(style="red", box=rich.box.ROUNDED)
            table.add_column(r"[✗] {} Test{} Failed".format(len(self.failed), _s(self.failed)), no_wrap=True)
            table = format_result(self.failed, table)
            console.print(table)

        # Summary table
        table = Table(box=rich.box.ROUNDED)
        table.add_column("[bold green]LINT RESULTS SUMMARY".format(len(self.passed)), no_wrap=True)
        table.add_row(r"[✔] {:>3} Test{} Passed".format(len(self.passed), _s(self.passed)), style="green")
        if len(self.fix):
            table.add_row(r"[?] {:>3} Test{} Fixed".format(len(self.fixed), _s(self.fixed)), style="bright_blue")
        table.add_row(r"[?] {:>3} Test{} Ignored".format(len(self.ignored), _s(self.ignored)), style="grey58")
        table.add_row(r"[!] {:>3} Test Warning{}".format(len(self.warned), _s(self.warned)), style="yellow")
        table.add_row(r"[✗] {:>3} Test{} Failed".format(len(self.failed), _s(self.failed)), style="red")
        console.print(table)

        if len(self.could_fix):
            fix_cmd = "nf-core lint {} --fix {}".format(self.wf_path, " --fix ".join(self.could_fix))
            console.print(
                f"\nTip: Some of these linting errors can automatically be resolved with the following command:\n\n[blue]    {fix_cmd}\n"
            )
        if len(self.fix):
            console.print(
                "Automatic fixes applied. Please check with 'git diff' and revert any changes you do not want with 'git checkout <file>'."
            )

    def _get_results_md(self):
        """
        Create a markdown file suitable for posting in a GitHub comment.

        Returns:
            markdown (str): Formatting markdown content
        """
        # Overall header
        overall_result = "Passed :white_check_mark:"
        if len(self.warned) > 0:
            overall_result += " :warning:"
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
                        "* [{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html) - {1}".format(
                            eid, self._strip_ansi_codes(msg, "`")
                        )
                        for eid, msg in self.failed
                    ]
                )
            )

        test_ignored_count = ""
        test_ignored = ""
        if len(self.ignored) > 0:
            test_ignored_count = "\n#| ❔ {:3d} tests were ignored |#".format(len(self.ignored))
            test_ignored = "### :grey_question: Tests ignored:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html) - {1}".format(
                            eid, self._strip_ansi_codes(msg, "`")
                        )
                        for eid, msg in self.ignored
                    ]
                )
            )

        test_fixed_count = ""
        test_fixed = ""
        if len(self.fixed) > 0:
            test_fixed_count = "\n#| ❔ {:3d} tests had warnings |#".format(len(self.fixed))
            test_fixed = "### :grey_question: Tests fixed:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html) - {1}".format(
                            eid, self._strip_ansi_codes(msg, "`")
                        )
                        for eid, msg in self.fixed
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
                        "* [{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html) - {1}".format(
                            eid, self._strip_ansi_codes(msg, "`")
                        )
                        for eid, msg in self.warned
                    ]
                )
            )

        test_passed_count = ""
        test_passes = ""
        if len(self.passed) > 0:
            test_passed_count = "\n+| ✅ {:3d} tests passed       |+".format(len(self.passed))
            test_passes = "### :white_check_mark: Tests passed:\n\n{}\n\n".format(
                "\n".join(
                    [
                        "* [{0}](https://nf-co.re/tools-docs/lint_tests/{0}.html) - {1}".format(
                            eid, self._strip_ansi_codes(msg, "`")
                        )
                        for eid, msg in self.passed
                    ]
                )
            )

        now = datetime.datetime.now()

        comment_body_text = "Posted for pipeline commit {}".format(self.git_sha[:7]) if self.git_sha is not None else ""
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        markdown = (
            f"## `nf-core lint` overall result: {overall_result}\n\n"
            f"{comment_body_text}\n\n"
            f"```diff{test_passed_count}{test_ignored_count}{test_fixed_count}{test_warning_count}{test_failure_count}\n"
            "```\n\n"
            "<details>\n"
            f"{test_failures}{test_warnings}{test_ignored}{test_fixed}{test_passes}### Run details\n\n"
            f"* nf-core/tools version {nf_core.__version__}\n"
            f"* Run at `{timestamp}`\n\n"
            "</details>\n"
        )

        return markdown

    def _save_json_results(self, json_fn):
        """
        Function to dump lint results to a JSON file for downstream use

        Arguments:
            json_fn (str): File path to write JSON to.
        """

        log.info("Writing lint results to {}".format(json_fn))
        now = datetime.datetime.now()
        results = {
            "nf_core_tools_version": nf_core.__version__,
            "date_run": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_pass": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.passed],
            "tests_ignored": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.ignored],
            "tests_fixed": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.fixed],
            "tests_warned": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.warned],
            "tests_failed": [[idx, self._strip_ansi_codes(msg)] for idx, msg in self.failed],
            "num_tests_pass": len(self.passed),
            "num_tests_ignored": len(self.ignored),
            "num_tests_fixed": len(self.fixed),
            "num_tests_warned": len(self.warned),
            "num_tests_failed": len(self.failed),
            "has_tests_pass": len(self.passed) > 0,
            "has_tests_ignored": len(self.ignored) > 0,
            "has_tests_fixed": len(self.fixed) > 0,
            "has_tests_warned": len(self.warned) > 0,
            "has_tests_failed": len(self.failed) > 0,
            "markdown_result": self._get_results_md(),
        }
        with open(json_fn, "w") as fh:
            json.dump(results, fh, indent=4)

    def _wrap_quotes(self, files):
        """Helper function to take a list of filenames and format with markdown.

        Args:
            files (list): List of filenames, eg::

                ['foo', 'bar', 'baz']

        Returns:
            markdown (str): Formatted string of paths separated by word ``or``, eg::

                `foo` or bar` or `baz`
        """
        if not isinstance(files, list):
            files = [files]
        bfiles = ["`{}`".format(f) for f in files]
        return " or ".join(bfiles)

    def _strip_ansi_codes(self, string, replace_with=""):
        """Strip ANSI colouring codes from a string to return plain text.

        Solution found on Stack Overflow: https://stackoverflow.com/a/14693789/713980
        """
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub(replace_with, string)
