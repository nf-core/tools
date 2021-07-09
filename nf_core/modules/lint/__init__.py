#!/usr/bin/env python
"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

from __future__ import print_function
import logging
from nf_core.modules.modules_command import ModuleCommand
import operator
import os
import questionary
import re
import requests
import rich
import yaml
import json
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
import rich
from nf_core.utils import rich_force_colors
from nf_core.lint.pipeline_todos import pipeline_todos
import sys

import nf_core.utils
import nf_core.modules.module_utils

from nf_core.modules.modules_repo import ModulesRepo
from nf_core.modules.nfcore_module import NFCoreModule
from nf_core.lint_utils import console

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
    from .functions_nf import functions_nf
    from .meta_yml import meta_yml
    from .module_changes import module_changes
    from .module_tests import module_tests
    from .module_todos import module_todos
    from .module_version import module_version

    def __init__(self, dir):
        self.dir = dir
        try:
            self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
        except LookupError as e:
            raise UserWarning(e)

        self.passed = []
        self.warned = []
        self.failed = []
        self.modules_repo = ModulesRepo()
        self.lint_tests = ["main_nf", "functions_nf", "meta_yml", "module_changes", "module_todos"]

        # Get lists of modules install in directory
        self.all_local_modules, self.all_nfcore_modules = self.get_installed_modules()

        self.lint_config = None
        self.modules_json = None

        # Add tests specific to nf-core/modules or pipelines
        if self.repo_type == "modules":
            self.lint_tests.append("module_tests")

        if self.repo_type == "pipeline":
            # Add as first test to load git_sha before module_changes
            self.lint_tests.insert(0, "module_version")

    def lint(self, module=None, key=(), all_modules=False, print_results=True, show_passed=False, local=False):
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
                    "choices": [m.module_name for m in self.all_nfcore_modules],
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
            nfcore_modules = [m for m in self.all_nfcore_modules if m.module_name == module]
            if len(nfcore_modules) == 0:
                raise ModuleLintException(f"Could not find the specified module: '{module}'")
        else:
            local_modules = self.all_local_modules
            nfcore_modules = self.all_nfcore_modules

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
            self.lint_modules(local_modules, local=True)

        # Lint nf-core modules
        if len(nfcore_modules) > 0:
            self.lint_modules(nfcore_modules, local=False)

        if print_results:
            self._print_results(show_passed=show_passed)
            self.print_summary()

    def set_up_pipeline_files(self):
        self.load_lint_config()
        self.modules_json = self.load_modules_json()

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
                    "s" if len(bad_keys) > 1 else "",
                    "', '".join(bad_keys),
                )
            )

        # If -k supplied, only run these tests
        self.lint_tests = [k for k in self.lint_tests if k in key]

    def get_installed_modules(self):
        """
        Makes lists of the local and and nf-core modules installed in this directory.

        Returns:
            local_modules, nfcore_modules ([NfCoreModule], [NfCoreModule]):
                A tuple of two lists: One for local modules and one for nf-core modules.
                In case the module contains several subtools, one path to each tool directory
                is returned.

        """
        # Initialize lists
        local_modules = []
        nfcore_modules = []
        local_modules_dir = None
        nfcore_modules_dir = os.path.join(self.dir, "modules", "nf-core", "modules")

        # Get local modules
        if self.repo_type == "pipeline":
            local_modules_dir = os.path.join(self.dir, "modules", "local")

            # Filter local modules
            if os.path.exists(local_modules_dir):
                local_modules = os.listdir(local_modules_dir)
                local_modules = sorted([x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")])

        # nf-core/modules
        if self.repo_type == "modules":
            nfcore_modules_dir = os.path.join(self.dir, "modules")

        # Get nf-core modules
        if os.path.exists(nfcore_modules_dir):
            for m in sorted([m for m in os.listdir(nfcore_modules_dir) if not m == "lib"]):
                if not os.path.isdir(os.path.join(nfcore_modules_dir, m)):
                    raise ModuleLintException(
                        f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                    )
                m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
                # Not a module, but contains sub-modules
                if not "main.nf" in m_content:
                    for tool in m_content:
                        nfcore_modules.append(os.path.join(m, tool))
                else:
                    nfcore_modules.append(m)

        # Create NFCoreModule objects for the nf-core and local modules
        nfcore_modules = [
            NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type=self.repo_type, base_dir=self.dir)
            for m in nfcore_modules
        ]

        local_modules = [
            NFCoreModule(
                os.path.join(local_modules_dir, m), repo_type=self.repo_type, base_dir=self.dir, nf_core_module=False
            )
            for m in local_modules
        ]

        # The local modules mustn't conform to the same file structure
        # as the nf-core modules. We therefore only check the main script
        # of the module
        for mod in local_modules:
            mod.main_nf = mod.module_dir
            mod.module_name = os.path.basename(mod.module_dir)

        return local_modules, nfcore_modules

    def lint_modules(self, modules, local=False):
        """
        Lint a list of modules

        Args:
            modules ([NFCoreModule]): A list of module objects
            local (boolean): Whether the list consist of local or nf-core modules
        """
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                f"Linting {'local' if local else 'nf-core'} modules",
                total=len(modules),
                test_name=modules[0].module_name,
            )

            for mod in modules:
                progress_bar.update(lint_progress, advance=1, test_name=mod.module_name)
                self.lint_module(mod, local=local)

    def lint_module(self, mod, local=False):
        """
        Perform linting on one module

        If the module is a local module we only check the `main.nf` file,
        and issue warnings instead of failures.

        If the module is a nf-core module we check for existence of the files
        - main.nf
        - meta.yml
        - functions.nf
        And verify that their content conform to the nf-core standards.

        If the linting is run for modules in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for module testing are
        also examined
        """

        # Only check the main script in case of a local module
        if local:
            self.main_nf(mod)
            self.passed += [LintResult(mod, *m) for m in mod.passed]
            self.warned += [LintResult(mod, *m) for m in mod.warned]

        # Otherwise run all the lint tests
        else:
            for test_name in self.lint_tests:
                getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, *m) for m in mod.passed]
            self.warned += [LintResult(mod, *m) for m in mod.warned]
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
        for idx, tests in enumerate([self.passed, self.warned, self.failed]):
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
            row_style = None
            for lint_result in test_results:
                if last_modname and lint_result.module_name != last_modname:
                    if row_style:
                        row_style = None
                    else:
                        row_style = "magenta"
                last_modname = lint_result.module_name
                table.add_row(
                    Markdown(f"{lint_result.module_name}"),
                    os.path.relpath(lint_result.file_path, self.dir),
                    Markdown(f"{lint_result.message}"),
                    style=row_style,
                )
            return table

        def _s(some_list):
            if len(some_list) > 1:
                return "s"
            return ""

        # Print module linting results header
        console.print(Panel("[magenta]Module lint results"))

        # Table of passed tests
        if len(self.passed) > 0 and show_passed:
            console.print(
                rich.panel.Panel(r"[!] {} Test{} Passed".format(len(self.passed), _s(self.passed)), style="bold green")
            )
            table = Table(style="green", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.passed, table)
            console.print(table)

        # Table of warning tests
        if len(self.warned) > 0:
            console.print(
                rich.panel.Panel(
                    r"[!] {} Test Warning{}".format(len(self.warned), _s(self.warned)), style="bold yellow"
                )
            )
            table = Table(style="yellow", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.warned, table)
            console.print(table)

        # Table of failing tests
        if len(self.failed) > 0:
            console.print(
                rich.panel.Panel(r"[!] {} Test{} Failed".format(len(self.failed), _s(self.failed)), style="bold red")
            )
            table = Table(style="red", box=rich.box.ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("File path")
            table.add_column("Test message")
            table = format_result(self.failed, table)
            console.print(table)

    def print_summary(self):
        def _s(some_list):
            if len(some_list) > 1:
                return "s"
            return ""

        # Summary table
        table = Table(box=rich.box.ROUNDED)
        table.add_column("[bold green]LINT RESULTS SUMMARY".format(len(self.passed)), no_wrap=True)
        table.add_row(
            r"[✔] {:>3} Test{} Passed".format(len(self.passed), _s(self.passed)),
            style="green",
        )
        table.add_row(r"[!] {:>3} Test Warning{}".format(len(self.warned), _s(self.warned)), style="yellow")
        table.add_row(r"[✗] {:>3} Test{} Failed".format(len(self.failed), _s(self.failed)), style="red")
        console.print(table)
