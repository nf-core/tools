"""
Code for linting modules and subworkflows in the nf-core/modules repository and
in nf-core pipelines
"""

import logging
import operator
import os
from pathlib import Path

import rich.box
import rich.console
import rich.panel
import rich.repr
from rich.markdown import Markdown
from rich.table import Table

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.lint_utils import console
from nf_core.modules.modules_json import ModulesJson
from nf_core.utils import plural_s as _s

log = logging.getLogger(__name__)


class LintExceptionError(Exception):
    """Exception raised when there was an error with module or subworkflow linting"""

    pass


@rich.repr.auto
class LintResult:
    """An object to hold the results of a lint test"""

    def __init__(self, component, lint_test, message, file_path):
        self.component = component
        self.lint_test = lint_test
        self.message = message
        self.file_path = file_path
        self.component_name = component.component_name


@rich.repr.auto
class ComponentLint(ComponentCommand):
    """
    An object for linting modules and subworkflows either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    def __init__(
        self,
        component_type,
        dir,
        fail_warned=False,
        remote_url=None,
        branch=None,
        no_pull=False,
        registry=None,
        hide_progress=False,
    ):
        super().__init__(
            component_type,
            dir=dir,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
            hide_progress=hide_progress,
        )

        self.fail_warned = fail_warned
        self.passed = []
        self.warned = []
        self.failed = []
        if self.component_type == "modules":
            self.lint_tests = self.get_all_module_lint_tests(self.repo_type == "pipeline")
        else:
            self.lint_tests = self.get_all_subworkflow_lint_tests(self.repo_type == "pipeline")

        if self.repo_type == "pipeline":
            modules_json = ModulesJson(self.dir)
            modules_json.check_up_to_date()
            self.all_remote_components = []
            for repo_url, components in modules_json.get_all_components(self.component_type).items():
                if remote_url is not None and remote_url != repo_url:
                    continue
                for org, comp in components:
                    self.all_remote_components.append(
                        NFCoreComponent(
                            comp,
                            repo_url,
                            Path(self.dir, self.component_type, org, comp),
                            self.repo_type,
                            Path(self.dir),
                            self.component_type,
                        )
                    )
            if not self.all_remote_components:
                raise LookupError(
                    f"No {self.component_type} from {self.modules_repo.remote_url} installed in pipeline."
                )
            local_component_dir = Path(self.dir, self.component_type, "local")
            self.all_local_components = []
            if local_component_dir.exists():
                self.all_local_components = [
                    NFCoreComponent(
                        comp,
                        None,
                        Path(local_component_dir, comp),
                        self.repo_type,
                        Path(self.dir),
                        self.component_type,
                        remote_component=False,
                    )
                    for comp in self.get_local_components()
                ]
            self.config = nf_core.utils.fetch_wf_config(self.dir, cache_config=True)
        else:
            component_dir = Path(
                self.dir,
                self.default_modules_path if self.component_type == "modules" else self.default_subworkflows_path,
            )
            self.all_remote_components = [
                NFCoreComponent(m, None, component_dir / m, self.repo_type, Path(self.dir), self.component_type)
                for m in self.get_components_clone_modules()
            ]
            self.all_local_components = []
            if not self.all_remote_components:
                raise LookupError(f"No {self.component_type} in '{self.component_type}' directory")

            # This could be better, perhaps glob for all nextflow.config files in?
            self.config = nf_core.utils.fetch_wf_config(Path(self.dir).joinpath("tests", "config"), cache_config=True)

        if registry is None:
            self.registry = self.config.get("docker.registry", "quay.io")
        else:
            self.registry = registry
        log.debug(f"Registry set to {self.registry}")

        self.lint_config = None
        self.modules_json = None

    @staticmethod
    def get_all_module_lint_tests(is_pipeline):
        if is_pipeline:
            return [
                "environment_yml",
                "module_patch",
                "module_version",
                "main_nf",
                "meta_yml",
                "module_todos",
                "module_deprecations",
                "module_changes",
            ]
        else:
            return ["environment_yml", "main_nf", "meta_yml", "module_todos", "module_deprecations", "module_tests"]

    @staticmethod
    def get_all_subworkflow_lint_tests(is_pipeline):
        if is_pipeline:
            return ["main_nf", "meta_yml", "subworkflow_changes", "subworkflow_todos", "subworkflow_version"]
        else:
            return ["main_nf", "meta_yml", "subworkflow_todos", "subworkflow_tests"]

    def set_up_pipeline_files(self):
        self.load_lint_config()
        self.modules_json = ModulesJson(self.dir)
        self.modules_json.load()

        # Only continue if a lint config has been loaded
        if self.lint_config:
            for test_name in self.lint_tests:
                if self.lint_config.get(test_name, {}) is False:
                    log.info(f"Ignoring lint test: {test_name}")
                    self.lint_tests.remove(test_name)

    def filter_tests_by_key(self, key):
        """Filters the tests by the supplied key"""
        # Check that supplied test keys exist
        bad_keys = [k for k in key if k not in self.lint_tests]
        if len(bad_keys) > 0:
            raise AssertionError(
                "Test name{} not recognised: '{}'".format(
                    _s(bad_keys),
                    "', '".join(bad_keys),
                )
            )

        # If -k supplied, only run these tests
        self.lint_tests = [k for k in self.lint_tests if k in key]

    def _print_results(self, show_passed=False, sort_by="test"):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")

        sort_order = ["lint_test", "component_name", "message"]
        if sort_by == "module" or sort_by == "subworkflow":
            sort_order = ["component_name", "lint_test", "message"]

        # Sort the results
        self.passed.sort(key=operator.attrgetter(*sort_order))
        self.warned.sort(key=operator.attrgetter(*sort_order))
        self.failed.sort(key=operator.attrgetter(*sort_order))

        # Find maximum module name length
        max_name_len = len(self.component_type[:-1] + " name")
        for tests in [self.passed, self.warned, self.failed]:
            try:
                for lint_result in tests:
                    max_name_len = max(len(lint_result.component_name), max_name_len)
            except Exception:
                pass

        # Helper function to format test links nicely
        def format_result(test_results, table):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            # TODO: Row styles don't work current as table-level style overrides.
            # Leaving it here in case there is a future fix
            last_modname = False
            even_row = False
            for lint_result in test_results:
                if last_modname and lint_result.component_name != last_modname:
                    even_row = not even_row
                last_modname = lint_result.component_name

                # If this is an nf-core module, link to the nf-core webpage
                if lint_result.component.repo_url == "https://github.com/nf-core/modules.git":
                    module_url = "https://nf-co.re/modules/" + lint_result.component_name.replace("/", "_")
                    module_name = f"[link={module_url}]{lint_result.component_name}[/link]"
                else:
                    module_name = lint_result.component_name

                # Make the filename clickable to open in VSCode
                file_path = os.path.relpath(lint_result.file_path, self.dir)
                file_path_link = f"[link=vscode://file/{os.path.abspath(file_path)}]{file_path}[/link]"

                table.add_row(
                    module_name,
                    file_path_link,
                    Markdown(f"{lint_result.message}"),
                    style="dim" if even_row else None,
                )
            return table

        # Print blank line for spacing
        console.print("")

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            table = Table(style="green", box=rich.box.MINIMAL, pad_edge=False, border_style="dim")
            table.add_column(f"{self.component_type[:-1].title()} name", width=max_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.passed, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][✔] {len(self.passed)} {self.component_type[:-1].title()} Test{_s(self.passed)} Passed",
                    title_align="left",
                    style="green",
                    padding=0,
                )
            )

        # Table of warning tests
        if len(self.warned) > 0:
            table = Table(style="yellow", box=rich.box.MINIMAL, pad_edge=False, border_style="dim")
            table.add_column(f"{self.component_type[:-1].title()} name", width=max_name_len)
            table.add_column("File path")
            table.add_column("Test message", overflow="fold")
            table = format_result(self.warned, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][!] {len(self.warned)} {self.component_type[:-1].title()} Test Warning{_s(self.warned)}",
                    title_align="left",
                    style="yellow",
                    padding=0,
                )
            )

        # Table of failing tests
        if len(self.failed) > 0:
            table = Table(
                style="red",
                box=rich.box.MINIMAL,
                pad_edge=False,
                border_style="dim",
            )
            table.add_column(f"{self.component_type[:-1].title()} name", width=max_name_len)
            table.add_column("File path")
            table.add_column("Test message", overflow="fold")
            table = format_result(self.failed, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][✗] {len(self.failed)} {self.component_type[:-1].title()} Test{_s(self.failed)} Failed",
                    title_align="left",
                    style="red",
                    padding=0,
                )
            )

    def print_summary(self):
        """Print a summary table to the console."""
        table = Table(box=rich.box.ROUNDED)
        table.add_column("[bold green]LINT RESULTS SUMMARY", no_wrap=True)
        table.add_row(
            rf"[✔] {len(self.passed):>3} Test{_s(self.passed)} Passed",
            style="green",
        )
        table.add_row(rf"[!] {len(self.warned):>3} Test Warning{_s(self.warned)}", style="yellow")
        table.add_row(rf"[✗] {len(self.failed):>3} Test{_s(self.failed)} Failed", style="red")
        console.print(table)
