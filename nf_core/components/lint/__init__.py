"""
Code for linting modules and subworkflows in the nf-core/modules repository and
in nf-core pipelines
"""

import logging
import operator
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import questionary
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
from nf_core.modules.modules_json import ModulesJson
from nf_core.pipelines.lint_utils import console
from nf_core.utils import NFCoreYamlLintConfig
from nf_core.utils import plural_s as _s

log = logging.getLogger(__name__)


class LintExceptionError(Exception):
    """Exception raised when there was an error with module or subworkflow linting"""

    pass


@rich.repr.auto
class LintResult:
    """An object to hold the results of a lint test"""

    def __init__(self, component: NFCoreComponent, lint_test: str, message: str, file_path: Path):
        self.component = component
        self.lint_test = lint_test
        self.message = message
        self.file_path = file_path
        self.component_name: str = component.component_name


class ComponentLint(ComponentCommand, ABC):
    """
    An object for linting modules and subworkflows either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    def __init__(
        self,
        component_type: str,
        directory: Union[str, Path],
        fail_warned: bool = False,
        fix: bool = False,
        remote_url: Optional[str] = None,
        branch: Optional[str] = None,
        no_pull: bool = False,
        registry: Optional[str] = None,
        hide_progress: bool = False,
    ):
        super().__init__(
            component_type,
            directory=directory,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
            hide_progress=hide_progress,
        )

        self.fail_warned = fail_warned
        self.fix = fix
        self.passed: list[LintResult] = []
        self.warned: list[LintResult] = []
        self.failed: list[LintResult] = []
        self.all_local_components: list[NFCoreComponent] = []

        self.lint_config: Optional[NFCoreYamlLintConfig] = None
        self.modules_json: Optional[ModulesJson] = None

        if self.component_type == "modules":
            self.lint_tests = self.get_all_module_lint_tests(self.repo_type == "pipeline")
        else:
            self.lint_tests = self.get_all_subworkflow_lint_tests(self.repo_type == "pipeline")

        if self.repo_type is None:
            raise LookupError(
                "Could not determine repository type. Please check the repository type in the nf-core.yml"
            )

        if self.repo_type == "pipeline":
            modules_json = ModulesJson(self.directory)
            modules_json.check_up_to_date()
            self.all_remote_components: list[NFCoreComponent] = []
            for repo_url, components in modules_json.get_all_components(self.component_type).items():
                if remote_url is not None and remote_url != repo_url:
                    continue
                if isinstance(components, str):
                    raise LookupError(
                        f"Error parsing modules.json: {components}. Please check the file for errors or try again."
                    )
                for org, comp in components:
                    self.all_remote_components.append(
                        NFCoreComponent(
                            comp,
                            repo_url,
                            Path(self.directory, self.component_type, org, comp),
                            self.repo_type,
                            self.directory,
                            self.component_type,
                        )
                    )
            if not self.all_remote_components:
                log.warning(f"No {self.component_type} from {self.modules_repo.remote_url} installed in pipeline.")
            local_component_dir = Path(self.directory, self.component_type, "local")

            if local_component_dir.exists():
                self.all_local_components = [
                    NFCoreComponent(
                        comp,
                        None,
                        Path(local_component_dir, comp),
                        self.repo_type,
                        self.directory,
                        self.component_type,
                        remote_component=False,
                    )
                    for comp in self.get_local_components()
                ]
            self.config = nf_core.utils.fetch_wf_config(self.directory, cache_config=True)
            self._set_registry(registry)

        elif self.repo_type == "modules":
            component_dir = Path(
                self.directory,
                self.default_modules_path if self.component_type == "modules" else self.default_subworkflows_path,
            )
            self.all_remote_components = [
                NFCoreComponent(m, None, component_dir / m, self.repo_type, self.directory, self.component_type)
                for m in self.get_components_clone_modules()
            ]
            self.all_local_components = []
            if not self.all_remote_components:
                log.warning(f"No {self.component_type} in '{self.component_type}' directory")

            # This could be better, perhaps glob for all nextflow.config files in?
            self.config = nf_core.utils.fetch_wf_config(self.directory / "tests" / "config", cache_config=True)
            self._set_registry(registry)

    def __repr__(self) -> str:
        return f"ComponentLint({self.component_type}, {self.directory})"

    def _set_registry(self, registry) -> None:
        if registry is None:
            self.registry = self.config.get("docker.registry", "quay.io")
        else:
            self.registry = registry
        log.debug(f"Registry set to {self.registry}")

    @property
    def local_module_exclude_tests(self):
        return ["module_version", "module_changes", "modules_patch"]

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
            return [
                "main_nf",
                "meta_yml",
                "subworkflow_changes",
                "subworkflow_todos",
                "subworkflow_if_empty_null",
                "subworkflow_version",
            ]
        else:
            return ["main_nf", "meta_yml", "subworkflow_todos", "subworkflow_if_empty_null", "subworkflow_tests"]

    def set_up_pipeline_files(self):
        self.load_lint_config()
        self.modules_json = ModulesJson(self.directory)
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
                file_path = os.path.relpath(lint_result.file_path, self.directory)
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

    def lint(
        self,
        component=None,
        registry="quay.io",
        key=(),
        all_components=False,
        print_results=True,
        show_passed=False,
        sort_by="test",
        local=False,
        fix_version=False,
    ):
        """
        Lint all or one specific component (unified method for modules and subworkflows)

        First gets a list of all local components and all components
        installed from nf-core.

        For all nf-core components, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the components are also inspected.

        For all local components, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param component:       A specific component to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well
        :param fix_version:     Update the component version if a newer version is available (modules only)
        :param hide_progress:   Don't show progress bars

        :returns:               A ComponentLint object containing information of
                                the passed, warned and failed tests
        """
        # Prompt for component or all
        if component is None and not (local or all_components) and len(self.all_remote_components) > 0:
            component_singular = self.component_type[:-1]  # modules -> module, subworkflows -> subworkflow
            questions = [
                {
                    "type": "list",
                    "name": f"all_{self.component_type}",
                    "message": f"Lint all {self.component_type} or a single named {component_singular}?",
                    "choices": [f"All {self.component_type}", f"Named {component_singular}"],
                },
                {
                    "type": "autocomplete",
                    "name": "component_name",
                    "message": f"{component_singular.title()} name:",
                    "when": lambda x: x[f"all_{self.component_type}"] == f"Named {component_singular}",
                    "choices": [m.component_name for m in self.all_remote_components],
                },
            ]
            answers = questionary.unsafe_prompt(questions, style=nf_core.utils.nfcore_question_style)
            all_components = answers[f"all_{self.component_type}"] == f"All {self.component_type}"
            component = answers.get("component_name")

        # Only lint the given component
        if component:
            if all_components:
                raise LintExceptionError("You cannot specify a tool and request all tools to be linted.")
            local_components = []
            remote_components = [c for c in self.all_remote_components if c.component_name == component]
            if len(remote_components) == 0:
                raise LintExceptionError(f"Could not find the specified {self.component_type[:-1]}: '{component}'")
        else:
            local_components = self.all_local_components
            remote_components = self.all_remote_components

        if self.repo_type == "modules":
            log.info(f"Linting modules repo: [magenta]'{self.directory}'")
        else:
            log.info(f"Linting pipeline: [magenta]'{self.directory}'")
        if component:
            log.info(f"Linting {self.component_type[:-1]}: [magenta]'{component}'")

        # Filter the tests by the key if one is supplied
        if key:
            self.filter_tests_by_key(key)
            log.info("Only running tests: '{}'".format("', '".join(key)))

        # If it is a pipeline, load the lint config file and the modules.json file
        if self.repo_type == "pipeline":
            self.set_up_pipeline_files()

        # Lint local components
        if local and len(local_components) > 0:
            self.lint_components(local_components, registry=registry, local=True, fix_version=fix_version)

        # Lint nf-core components
        if not local and len(remote_components) > 0:
            self.lint_components(remote_components, registry=registry, local=False, fix_version=fix_version)

        if print_results:
            self._print_results(show_passed=show_passed, sort_by=sort_by)
            self.print_summary()

    def lint_components(
        self,
        components: list[NFCoreComponent],
        registry: str = "quay.io",
        local: bool = False,
        fix_version: bool = False,
    ) -> None:
        """
        Lint a list of components

        Args:
            components ([NFCoreComponent]): A list of component objects
            registry (str): The container registry to use. Should be quay.io in most situations.
            local (boolean): Whether the list consist of local or nf-core components
            fix_version (boolean): Fix the component version if a newer version is available (modules only)
        """
        import rich.progress

        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
            console=console,
            disable=self.hide_progress or os.environ.get("HIDE_PROGRESS", None) is not None,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                f"Linting {'local' if local else 'nf-core'} {self.component_type}",
                total=len(components),
                test_name=components[0].component_name,
            )

            for component in components:
                progress_bar.update(lint_progress, advance=1, test_name=component.component_name)
                self.lint_component(component, progress_bar, local=local, fix_version=fix_version, registry=registry)

    def lint_component(
        self,
        component: NFCoreComponent,
        progress_bar,
        local: bool = False,
        fix_version: bool = False,
        registry: str = "quay.io",
    ):
        """
        Perform linting on one component (template method)

        If the component is a local component we only check the `main.nf` file,
        and issue warnings instead of failures.

        If the component is a nf-core component we check for existence of the files
        - main.nf
        - meta.yml
        And verify that their content conform to the nf-core standards.

        If the linting is run for components in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for component testing are
        also examined
        """
        if local:
            self._lint_local_component(component, fix_version=fix_version, registry=registry, progress_bar=progress_bar)
        else:
            self._lint_remote_component(
                component, fix_version=fix_version, registry=registry, progress_bar=progress_bar
            )

        # Aggregate results
        self._aggregate_component_results(component)

    def _aggregate_component_results(self, component: NFCoreComponent):
        """Aggregate component results into the main results lists"""
        self.passed += [LintResult(component, *m) for m in component.passed]

        # Handle warnings differently for local vs remote components
        if hasattr(self, "_is_local_linting") and self._is_local_linting:
            warned = [LintResult(component, *m) for m in (component.warned + component.failed)]
        else:
            warned = [LintResult(component, *m) for m in component.warned]
            self.failed += [LintResult(component, *m) for m in component.failed]

        if not self.fail_warned:
            self.warned += warned
        else:
            self.failed += warned

    # Abstract methods for child classes to implement
    @abstractmethod
    def _lint_local_component(self, component: NFCoreComponent, **kwargs):
        """Lint a local component. Must be implemented by child classes."""
        pass

    @abstractmethod
    def _lint_remote_component(self, component: NFCoreComponent, **kwargs):
        """Lint a remote component. Must be implemented by child classes."""
        pass
