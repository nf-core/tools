#!/usr/bin/env python
"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

from __future__ import print_function

import logging
import operator
import os
from pathlib import Path

import questionary
import rich
from rich.markdown import Markdown
from rich.table import Table

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.lint_utils import console
from nf_core.modules.modules_command import ModuleCommand
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import ModulesRepo
from nf_core.modules.nfcore_module import NFCoreModule
from nf_core.utils import plural_s as _s

log = logging.getLogger(__name__)


class ModuleLintException(Exception):
    """Exception raised when there was an error with module linting"""

    pass


class LintResult(object):
    """An object to hold the results of a lint test"""

    def __init__(self, mod, lint_test, message, file_path):
        self.mod = mod
        self.lint_test = lint_test
        self.message = message
        self.file_path = file_path
        self.module_name = mod.module_name


class ModuleLint(ModuleCommand):
    """
    An object for linting modules either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    # Import lint functions
    from .main_nf import main_nf
    from .meta_yml import meta_yml
    from .module_changes import module_changes
    from .module_deprecations import module_deprecations
    from .module_patch import module_patch
    from .module_tests import module_tests
    from .module_todos import module_todos
    from .module_version import module_version

    def __init__(
        self,
        dir,
        fail_warned=False,
        remote_url=None,
        branch=None,
        no_pull=False,
        hide_progress=False,
    ):
        super().__init__(dir=dir, remote_url=remote_url, branch=branch, no_pull=no_pull, hide_progress=False)

        self.fail_warned = fail_warned
        self.passed = []
        self.warned = []
        self.failed = []
        self.lint_tests = self.get_all_lint_tests(self.repo_type == "pipeline")

        if self.repo_type == "pipeline":
            modules_json = ModulesJson(self.dir)
            modules_json.check_up_to_date()
            all_pipeline_modules = modules_json.get_all_modules()
            if self.modules_repo.fullname in all_pipeline_modules:
                module_dir = Path(self.dir, "modules", self.modules_repo.fullname)
                self.all_remote_modules = [
                    NFCoreModule(m, self.modules_repo.fullname, module_dir / m, self.repo_type, Path(self.dir))
                    for m in all_pipeline_modules[self.modules_repo.fullname]
                ]
                if not self.all_remote_modules:
                    raise LookupError(f"No modules from {self.modules_repo.remote_url} installed in pipeline.")
                local_module_dir = Path(self.dir, "modules", "local")
                self.all_local_modules = [
                    NFCoreModule(m, None, local_module_dir / m, self.repo_type, Path(self.dir), nf_core_module=False)
                    for m in self.get_local_modules()
                ]

            else:
                raise LookupError(f"No modules from {self.modules_repo.remote_url} installed in pipeline.")
        else:
            module_dir = Path(self.dir, "modules")
            self.all_remote_modules = [
                NFCoreModule(m, None, module_dir / m, self.repo_type, Path(self.dir))
                for m in self.get_modules_clone_modules()
            ]
            self.all_local_modules = []
            if not self.all_remote_modules:
                raise LookupError("No modules in 'modules' directory")

        self.lint_config = None
        self.modules_json = None

    @staticmethod
    def get_all_lint_tests(is_pipeline):
        if is_pipeline:
            return [
                "module_patch",
                "module_version",
                "main_nf",
                "meta_yml",
                "module_todos",
                "module_deprecations",
                "module_changes",
            ]
        else:
            return ["main_nf", "meta_yml", "module_todos", "module_deprecations", "module_tests"]

    def lint(
        self,
        module=None,
        key=(),
        all_modules=False,
        hide_progress=False,
        print_results=True,
        show_passed=False,
        local=False,
        fix_version=False,
    ):
        """
        Lint all or one specific module

        First gets a list of all local modules (in modules/local/process) and all modules
        installed from nf-core (in modules/nf-core/modules)

        For all nf-core modules, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the modules are also inspected.

        For all local modules, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param module:          A specific module to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well
        :param fix_version:     Update the module version if a newer version is available
        :param hide_progress:   Don't show progress bars

        :returns:               A ModuleLint object containing information of
                                the passed, warned and failed tests
        """

        # Prompt for module or all
        if module is None and not all_modules:
            questions = [
                {
                    "type": "list",
                    "name": "all_modules",
                    "message": "Lint all modules or a single named module?",
                    "choices": ["All modules", "Named module"],
                },
                {
                    "type": "autocomplete",
                    "name": "tool_name",
                    "message": "Tool name:",
                    "when": lambda x: x["all_modules"] == "Named module",
                    "choices": [m.module_name for m in self.all_remote_modules],
                },
            ]
            answers = questionary.unsafe_prompt(questions, style=nf_core.utils.nfcore_question_style)
            all_modules = answers["all_modules"] == "All modules"
            module = answers.get("tool_name")

        # Only lint the given module
        if module:
            if all_modules:
                raise ModuleLintException("You cannot specify a tool and request all tools to be linted.")
            local_modules = []
            remote_modules = [m for m in self.all_remote_modules if m.module_name == module]
            if len(remote_modules) == 0:
                raise ModuleLintException(f"Could not find the specified module: '{module}'")
        else:
            local_modules = self.all_local_modules
            remote_modules = self.all_remote_modules

        if self.repo_type == "modules":
            log.info(f"Linting modules repo: [magenta]'{self.dir}'")
        else:
            log.info(f"Linting pipeline: [magenta]'{self.dir}'")
        if module:
            log.info(f"Linting module: [magenta]'{module}'")

        # Filter the tests by the key if one is supplied
        if key:
            self.filter_tests_by_key(key)
            log.info("Only running tests: '{}'".format("', '".join(key)))

        # If it is a pipeline, load the lint config file and the modules.json file
        if self.repo_type == "pipeline":
            self.set_up_pipeline_files()

        # Lint local modules
        if local and len(local_modules) > 0:
            self.lint_modules(local_modules, local=True, fix_version=fix_version)

        # Lint nf-core modules
        if len(remote_modules) > 0:
            self.lint_modules(remote_modules, local=False, fix_version=fix_version)

        if print_results:
            self._print_results(show_passed=show_passed)
            self.print_summary()

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

    def lint_modules(self, modules, local=False, fix_version=False):
        """
        Lint a list of modules

        Args:
            modules ([NFCoreModule]): A list of module objects
            local (boolean): Whether the list consist of local or nf-core modules
            fix_version (boolean): Fix the module version if a newer version is available
        """
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
            console=console,
            disable=self.hide_progress,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                f"Linting {'local' if local else 'nf-core'} modules",
                total=len(modules),
                test_name=modules[0].module_name,
            )

            for mod in modules:
                progress_bar.update(lint_progress, advance=1, test_name=mod.module_name)
                self.lint_module(mod, progress_bar, local=local, fix_version=fix_version)

    def lint_module(self, mod, progress_bar, local=False, fix_version=False):
        """
        Perform linting on one module

        If the module is a local module we only check the `main.nf` file,
        and issue warnings instead of failures.

        If the module is a nf-core module we check for existence of the files
        - main.nf
        - meta.yml
        And verify that their content conform to the nf-core standards.

        If the linting is run for modules in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for module testing are
        also examined
        """

        # Only check the main script in case of a local module
        if local:
            self.main_nf(mod, fix_version, progress_bar)
            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in (mod.warned + mod.failed)]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

        # Otherwise run all the lint tests
        else:
            for test_name in self.lint_tests:
                if test_name == "main_nf":
                    getattr(self, test_name)(mod, fix_version, progress_bar)
                else:
                    getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in mod.warned]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

            self.failed += [LintResult(mod, *m) for m in mod.failed]

    def _print_results(self, show_passed=False):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")

        # Sort the results
        self.passed.sort(key=operator.attrgetter("message", "module_name"))
        self.warned.sort(key=operator.attrgetter("message", "module_name"))
        self.failed.sort(key=operator.attrgetter("message", "module_name"))

        # Find maximum module name length
        max_mod_name_len = 40
        for tests in [self.passed, self.warned, self.failed]:
            try:
                for lint_result in tests:
                    max_mod_name_len = max(len(lint_result.module_name), max_mod_name_len)
            except:
                pass

        # Helper function to format test links nicely
        def format_result(test_results, table):
            """
            Given an list of error message IDs and the message texts, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            # TODO: Row styles don't work current as table-level style overrides.
            # I'd like to make an issue about this on the rich repo so leaving here in case there is a future fix
            last_modname = False
            even_row = False
            for lint_result in test_results:
                if last_modname and lint_result.module_name != last_modname:
                    even_row = not even_row
                last_modname = lint_result.module_name
                table.add_row(
                    Markdown(f"{lint_result.module_name}"),
                    os.path.relpath(lint_result.file_path, self.dir),
                    Markdown(f"{lint_result.message}"),
                    style="dim" if even_row else None,
                )
            return table

        # Print blank line for spacing
        console.print("")

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            table = Table(style="green", box=rich.box.MINIMAL, pad_edge=False, border_style="dim")
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.passed, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][✔] {len(self.passed)} Module Test{_s(self.passed)} Passed",
                    title_align="left",
                    style="green",
                    padding=0,
                )
            )

        # Table of warning tests
        if len(self.warned) > 0:
            table = Table(style="yellow", box=rich.box.MINIMAL, pad_edge=False, border_style="dim")
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.warned, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][!] {len(self.warned)} Module Test Warning{_s(self.warned)}",
                    title_align="left",
                    style="yellow",
                    padding=0,
                )
            )

        # Table of failing tests
        if len(self.failed) > 0:
            table = Table(style="red", box=rich.box.MINIMAL, pad_edge=False, border_style="dim")
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.failed, table)
            console.print(
                rich.panel.Panel(
                    table,
                    title=rf"[bold][✗] {len(self.failed)} Module Test{_s(self.failed)} Failed",
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
