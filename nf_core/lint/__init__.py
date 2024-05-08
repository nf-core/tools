"""Linting policy for nf-core pipeline projects.

Tests Nextflow-based pipelines to check that they adhere to
the nf-core community guidelines.
"""

import datetime
import json
import logging
import os
from pathlib import Path
from typing import List, Tuple, Union

import git
import rich
import rich.progress
from git.exc import InvalidGitRepositoryError
from rich.console import group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

import nf_core.lint_utils
import nf_core.modules.lint
import nf_core.subworkflows.lint
import nf_core.utils
from nf_core import __version__
from nf_core.components.lint import ComponentLint
from nf_core.lint_utils import console
from nf_core.utils import plural_s as _s
from nf_core.utils import strip_ansi_codes

log = logging.getLogger(__name__)


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

    from .actions_awsfulltest import actions_awsfulltest  # type: ignore[misc]
    from .actions_awstest import actions_awstest  # type: ignore[misc]
    from .actions_ci import actions_ci  # type: ignore[misc]
    from .actions_schema_validation import (  # type: ignore[misc]
        actions_schema_validation,
    )
    from .configs import base_config, modules_config  # type: ignore[misc]
    from .files_exist import files_exist  # type: ignore[misc]
    from .files_unchanged import files_unchanged  # type: ignore[misc]
    from .merge_markers import merge_markers  # type: ignore[misc]
    from .modules_json import modules_json  # type: ignore[misc]
    from .modules_structure import modules_structure  # type: ignore[misc]
    from .multiqc_config import multiqc_config  # type: ignore[misc]
    from .nextflow_config import nextflow_config  # type: ignore[misc]
    from .nfcore_yml import nfcore_yml  # type: ignore[misc]
    from .pipeline_name_conventions import (  # type: ignore[misc]
        pipeline_name_conventions,
    )
    from .pipeline_todos import pipeline_todos  # type: ignore[misc]
    from .readme import readme  # type: ignore[misc]
    from .schema_description import schema_description  # type: ignore[misc]
    from .schema_lint import schema_lint  # type: ignore[misc]
    from .schema_params import schema_params  # type: ignore[misc]
    from .system_exit import system_exit  # type: ignore[misc]
    from .template_strings import template_strings  # type: ignore[misc]
    from .version_consistency import version_consistency  # type: ignore[misc]

    def __init__(
        self, wf_path, release_mode=False, fix=(), key=None, fail_ignored=False, fail_warned=False, hide_progress=False
    ):
        """Initialise linting object"""

        # Initialise the parent object
        super().__init__(wf_path)

        self.lint_config = {}
        self.release_mode = release_mode
        self.fail_ignored = fail_ignored
        self.fail_warned = fail_warned
        self.hide_progress = hide_progress
        self.failed = []
        self.ignored = []
        self.fixed = []
        self.passed = []
        self.warned = []
        self.could_fix = []
        self.lint_tests = self._get_all_lint_tests(self.release_mode)
        self.fix = fix
        self.key = key
        self.progress_bar = None

    @staticmethod
    def _get_all_lint_tests(release_mode):
        return [
            "files_exist",
            "nextflow_config",
            "files_unchanged",
            "actions_ci",
            "actions_awstest",
            "actions_awsfulltest",
            "readme",
            "pipeline_todos",
            "pipeline_name_conventions",
            "template_strings",
            "schema_lint",
            "schema_params",
            "system_exit",
            "schema_description",
            "actions_schema_validation",
            "merge_markers",
            "modules_json",
            "multiqc_config",
            "modules_structure",
            "base_config",
            "modules_config",
            "nfcore_yml",
        ] + (["version_consistency"] if release_mode else [])

    def _load(self):
        """Load information about the pipeline into the PipelineLint object"""
        # Load everything using the parent object
        super()._load()

        # Load lint object specific stuff
        self._load_lint_config()

    def _load_lint_config(self):
        """Parse a pipeline lint config file.

        Load the '.nf-core.yml'  config file and extract
        the lint config from it

        Add parsed config to the `self.lint_config` class attribute.
        """
        _, tools_config = nf_core.utils.load_tools_config(self.wf_path)
        self.lint_config = tools_config.get("lint", {})

        # Check if we have any keys that don't match lint test names
        for k in self.lint_config:
            if k not in self.lint_tests:
                log.warning(f"Found unrecognised test name '{k}' in pipeline lint config")

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
                    _s(unrecognised_fixes), "', '".join(unrecognised_fixes)
                )
            )

        if self.key is not None:
            # Check that supplied test keys exist
            bad_keys = [k for k in self.key if k not in self.lint_tests]
            if len(bad_keys) > 0:
                raise AssertionError(
                    "Test name{} not recognised: '{}'".format(
                        _s(bad_keys),
                        "', '".join(bad_keys),
                    )
                )

            # If -k supplied, only run these tests
            self.lint_tests = [k for k in self.lint_tests if k in self.key]
            if len(self.lint_tests) == 0:
                log.debug("No pipeline lint tests to run")
                return

        # Check that the pipeline_dir is a clean git repo
        if len(self.fix):
            log.info("Attempting to automatically fix failing tests")
            try:
                repo = git.Repo(self.wf_path)
            except InvalidGitRepositoryError:
                raise AssertionError(
                    f"'{self.wf_path}' does not appear to be a git repository, "
                    "this is required when running with '--fix'"
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
            disable=self.hide_progress or os.environ.get("HIDE_PROGRESS", None) is not None,
        )
        with self.progress_bar:
            lint_progress = self.progress_bar.add_task(
                "Running lint checks", total=len(self.lint_tests), test_name=self.lint_tests[0]
            )
            for test_name in self.lint_tests:
                if self.lint_config.get(test_name, {}) is False:
                    log.debug(f"Skipping lint test '{test_name}'")
                    self.ignored.append((test_name, test_name))
                    continue
                self.progress_bar.update(lint_progress, advance=1, test_name=test_name)
                log.debug(f"Running lint test: {test_name}")
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
                    if self.fail_warned:
                        self.failed.append((test_name, test))
                    else:
                        self.warned.append((test_name, test))
                for test in test_results.get("failed", []):
                    self.failed.append((test_name, test))
                if test_results.get("could_fix", False):
                    self.could_fix.append(test_name)

    def _print_results(self, show_passed):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        # Spacing from log messages above
        console.print("")

        log.debug("Printing final results")

        # Helper function to format test links nicely
        @group()
        def format_result(test_results):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            tools_version = __version__
            if "dev" in __version__:
                tools_version = "latest"
            for eid, msg in test_results:
                yield Markdown(f"[{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}): {msg}")

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            console.print(
                Panel(
                    format_result(self.passed),
                    title=rf"[bold][✔] {len(self.passed)} Pipeline Test{_s(self.passed)} Passed",
                    title_align="left",
                    style="green",
                    padding=1,
                )
            )

        # Table of fixed tests
        if len(self.fixed) > 0:
            console.print(
                Panel(
                    format_result(self.fixed),
                    title=rf"[bold][?] {len(self.fixed)} Pipeline Test{_s(self.fixed)} Fixed",
                    title_align="left",
                    style="bright_blue",
                    padding=1,
                )
            )

        # Table of ignored tests
        if len(self.ignored) > 0:
            console.print(
                Panel(
                    format_result(self.ignored),
                    title=rf"[bold][?] {len(self.ignored)} Pipeline Test{_s(self.ignored)} Ignored",
                    title_align="left",
                    style="grey58",
                    padding=1,
                )
            )

        # Table of warning tests
        if len(self.warned) > 0:
            console.print(
                Panel(
                    format_result(self.warned),
                    title=rf"[bold][!] {len(self.warned)} Pipeline Test Warning{_s(self.warned)}",
                    title_align="left",
                    style="yellow",
                    padding=1,
                )
            )

        # Table of failing tests
        if len(self.failed) > 0:
            console.print(
                Panel(
                    format_result(self.failed),
                    title=rf"[bold][✗] {len(self.failed)} Pipeline Test{_s(self.failed)} Failed",
                    title_align="left",
                    style="red",
                    padding=1,
                )
            )

    def _print_summary(self):
        # Summary table
        summary_colour = "red" if len(self.failed) > 0 else "green"
        table = Table(box=rich.box.ROUNDED, style=summary_colour)
        table.add_column("LINT RESULTS SUMMARY", no_wrap=True)
        table.add_row(rf"[green][✔] {len(self.passed):>3} Test{_s(self.passed)} Passed")
        if len(self.fix):
            table.add_row(rf"[bright blue][?] {len(self.fixed):>3} Test{_s(self.fixed)} Fixed")
        table.add_row(rf"[grey58][?] {len(self.ignored):>3} Test{_s(self.ignored)} Ignored")
        table.add_row(rf"[yellow][!] {len(self.warned):>3} Test Warning{_s(self.warned)}")
        table.add_row(rf"[red][✗] {len(self.failed):>3} Test{_s(self.failed)} Failed")
        console.print(table)

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

        tools_version = __version__
        if "dev" in __version__:
            tools_version = "latest"

        # List of tests for details
        test_failure_count = ""
        test_failures = ""
        if len(self.failed) > 0:
            test_failure_count = f"\n-| ❌ {len(self.failed):3d} tests failed       |-"
            test_failures = "### :x: Test failures:\n\n{}\n\n".format(
                "\n".join(
                    [
                        f"* [{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}) - "
                        f"{strip_ansi_codes(msg, '`')}"
                        for eid, msg in self.failed
                    ]
                )
            )

        test_ignored_count = ""
        test_ignored = ""
        if len(self.ignored) > 0:
            test_ignored_count = f"\n#| ❔ {len(self.ignored):3d} tests were ignored |#"
            test_ignored = "### :grey_question: Tests ignored:\n\n{}\n\n".format(
                "\n".join(
                    [
                        f"* [{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}) - "
                        f"{strip_ansi_codes(msg, '`')}"
                        for eid, msg in self.ignored
                    ]
                )
            )

        test_fixed_count = ""
        test_fixed = ""
        if len(self.fixed) > 0:
            test_fixed_count = f"\n#| ❔ {len(self.fixed):3d} tests had warnings |#"
            test_fixed = "### :grey_question: Tests fixed:\n\n{}\n\n".format(
                "\n".join(
                    [
                        f"* [{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}) - "
                        f"{strip_ansi_codes(msg, '`')}"
                        for eid, msg in self.fixed
                    ]
                )
            )

        test_warning_count = ""
        test_warnings = ""
        if len(self.warned) > 0:
            test_warning_count = f"\n!| ❗ {len(self.warned):3d} tests had warnings |!"
            test_warnings = "### :heavy_exclamation_mark: Test warnings:\n\n{}\n\n".format(
                "\n".join(
                    [
                        f"* [{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid}) - "
                        f"{strip_ansi_codes(msg, '`')}"
                        for eid, msg in self.warned
                    ]
                )
            )

        test_passed_count = ""
        test_passes = ""
        if len(self.passed) > 0:
            test_passed_count = f"\n+| ✅ {len(self.passed):3d} tests passed       |+"
            test_passes = "### :white_check_mark: Tests passed:\n\n{}\n\n".format(
                "\n".join(
                    [
                        (
                            f"* [{eid}](https://nf-co.re/tools/docs/{tools_version}/pipeline_lint_tests/{eid})"
                            f" - {strip_ansi_codes(msg, '`')}"
                        )
                        for eid, msg in self.passed
                    ]
                )
            )

        now = datetime.datetime.now()

        comment_body_text = f"Posted for pipeline commit {self.git_sha[:7]}" if self.git_sha is not None else ""
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        markdown = (
            f"## `nf-core lint` overall result: {overall_result}\n\n"
            f"{comment_body_text}\n\n"
            f"```diff{test_passed_count}{test_ignored_count}{test_fixed_count}{test_warning_count}{test_failure_count}"
            "\n```\n\n"
            "<details>\n\n"
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

        log.info(f"Writing lint results to {json_fn}")
        now = datetime.datetime.now()
        results = {
            "nf_core_tools_version": nf_core.__version__,
            "date_run": now.strftime("%Y-%m-%d %H:%M:%S"),
            "tests_pass": [[idx, strip_ansi_codes(msg)] for idx, msg in self.passed],
            "tests_ignored": [[idx, strip_ansi_codes(msg)] for idx, msg in self.ignored],
            "tests_fixed": [[idx, strip_ansi_codes(msg)] for idx, msg in self.fixed],
            "tests_warned": [[idx, strip_ansi_codes(msg)] for idx, msg in self.warned],
            "tests_failed": [[idx, strip_ansi_codes(msg)] for idx, msg in self.failed],
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

    def _wrap_quotes(self, files: Union[List[str], List[Path], Path]) -> str:
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
        bfiles = [f"`{str(f)}`" for f in files]
        return " or ".join(bfiles)


def run_linting(
    pipeline_dir,
    release_mode: bool = False,
    fix=(),
    key=(),
    show_passed: bool = False,
    fail_ignored: bool = False,
    fail_warned: bool = False,
    sort_by: str = "test",
    md_fn=None,
    json_fn=None,
    hide_progress: bool = False,
) -> Tuple[PipelineLint, ComponentLint, Union[ComponentLint, None]]:
    """Runs all nf-core linting checks on a given Nextflow pipeline project
    in either `release` mode or `normal` mode (default). Returns an object
    of type :class:`PipelineLint` after finished.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        release_mode (bool): Set this to `True`, if the linting should be run in the `release` mode.
                             See :class:`PipelineLint` for more information.

    Returns:
        An object of type :class:`PipelineLint` that contains all the linting results.
        An object of type :class:`ComponentLint` that contains all the linting results for the modules.
        An object of type :class:`ComponentLint` that contains all the linting results for the subworkflows.
    """

    # Verify that the requested tests exist
    if key:
        all_tests = set(PipelineLint._get_all_lint_tests(release_mode)).union(
            set(nf_core.modules.lint.ModuleLint.get_all_module_lint_tests(is_pipeline=True))
        )
        bad_keys = [k for k in key if k not in all_tests]
        if len(bad_keys) > 0:
            raise AssertionError(
                "Test name{} not recognised: '{}'".format(
                    _s(bad_keys),
                    "', '".join(bad_keys),
                )
            )
        log.info("Only running tests: '{}'".format("', '".join(key)))

    # Check if we were given any keys, and if they match any pipeline tests
    if key:
        pipeline_keys = list(set(key).intersection(set(PipelineLint._get_all_lint_tests(release_mode))))
    else:
        # If no key is supplied, run all tests
        pipeline_keys = None

    # Create the lint object
    lint_obj = PipelineLint(pipeline_dir, release_mode, fix, pipeline_keys, fail_ignored, fail_warned, hide_progress)

    # Load the various pipeline configs
    lint_obj._load_lint_config()
    lint_obj._load_pipeline_config()
    lint_obj._list_files()

    # Create the modules lint object
    module_lint_obj = nf_core.modules.lint.ModuleLint(pipeline_dir, hide_progress=hide_progress)
    # Create the subworkflows lint object
    try:
        subworkflow_lint_obj = nf_core.subworkflows.lint.SubworkflowLint(pipeline_dir, hide_progress=hide_progress)
    except LookupError:
        subworkflow_lint_obj = None

    # Verify that the pipeline is correctly configured and has  a modules.json file
    module_lint_obj.has_valid_directory()
    module_lint_obj.has_modules_file()
    # Run only the tests we want
    if key:
        # Select only the module lint tests
        module_lint_tests = list(
            set(key).intersection(set(nf_core.modules.lint.ModuleLint.get_all_module_lint_tests(is_pipeline=True)))
        )
        # Select only the subworkflow lint tests
        subworkflow_lint_tests = list(
            set(key).intersection(
                set(nf_core.subworkflows.lint.SubworkflowLint.get_all_subworkflow_lint_tests(is_pipeline=True))
            )
        )
    else:
        # If no key is supplied, run the default modules tests
        module_lint_tests = list(("module_changes", "module_version"))
        subworkflow_lint_tests = list(("subworkflow_changes", "subworkflow_version"))
    module_lint_obj.filter_tests_by_key(module_lint_tests)
    if subworkflow_lint_obj is not None:
        subworkflow_lint_obj.filter_tests_by_key(subworkflow_lint_tests)

    # Set up files for component linting test
    module_lint_obj.set_up_pipeline_files()
    if subworkflow_lint_obj is not None:
        subworkflow_lint_obj.set_up_pipeline_files()

    # Run the pipeline linting tests
    try:
        lint_obj._lint_pipeline()
    except AssertionError as e:
        log.critical(f"Critical error: {e}")
        log.info("Stopping tests...")
        return lint_obj, module_lint_obj, subworkflow_lint_obj

    # Run the module lint tests
    if len(module_lint_obj.all_local_components) > 0:
        module_lint_obj.lint_modules(module_lint_obj.all_local_components, local=True)
    if len(module_lint_obj.all_remote_components) > 0:
        module_lint_obj.lint_modules(module_lint_obj.all_remote_components, local=False)
    # Run the subworkflows lint tests
    if subworkflow_lint_obj is not None:
        if len(subworkflow_lint_obj.all_local_components) > 0:
            subworkflow_lint_obj.lint_subworkflows(subworkflow_lint_obj.all_local_components, local=True)
        if len(subworkflow_lint_obj.all_remote_components) > 0:
            subworkflow_lint_obj.lint_subworkflows(subworkflow_lint_obj.all_remote_components, local=False)

    # Print the results
    lint_obj._print_results(show_passed)
    module_lint_obj._print_results(show_passed, sort_by=sort_by)
    if subworkflow_lint_obj is not None:
        subworkflow_lint_obj._print_results(show_passed, sort_by=sort_by)
    nf_core.lint_utils.print_joint_summary(lint_obj, module_lint_obj, subworkflow_lint_obj)
    nf_core.lint_utils.print_fixes(lint_obj)

    # Save results to Markdown file
    if md_fn is not None:
        log.info(f"Writing lint results to {md_fn}")
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

    return lint_obj, module_lint_obj, subworkflow_lint_obj
