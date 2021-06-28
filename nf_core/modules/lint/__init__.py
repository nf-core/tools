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
import questionary
import re
import requests
import rich
import yaml
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
import rich
from nf_core.utils import rich_force_colors
from nf_core.lint.pipeline_todos import pipeline_todos
import sys

import nf_core.utils
import nf_core.modules.module_utils
from nf_core.modules.modules_repo import ModulesRepo
from nf_core.modules.nfcore_module import NFCoreModule


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


class ModuleLint(object):
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

    def __init__(self, dir, key=()):
        self.dir = dir
        self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
        self.passed = []
        self.warned = []
        self.failed = []
        self.modules_repo = ModulesRepo()
        self.lint_tests = ["main_nf", "functions_nf", "meta_yml", "module_changes", "module_todos"]
        self.key = key
        self.lint_config = None

        # Add tests specific to nf-core/modules
        if self.repo_type == "modules":
            self.lint_tests.append("module_tests")

    def lint(self, module=None, all_modules=False, print_results=True, show_passed=False, local=False):
        """
        Lint all or one specific module

        First gets a list of all local modules (in modules/local/process) and all modules
        installed from nf-core (in modules/nf-core/software)

        For all nf-core modules, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the modules are also inspected.

        For all local modules, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param module:          A specific module to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well

        :returns:               dict of {passed, warned, failed}
        """

        # Get list of all modules in a pipeline
        local_modules, nfcore_modules = self.get_installed_modules()

        # Prompt for module or all
        if module is None and not all_modules:
            question = {
                "type": "list",
                "name": "all_modules",
                "message": "Lint all modules or a single named module?",
                "choices": ["All modules", "Named module"],
            }
            answer = questionary.unsafe_prompt([question], style=nf_core.utils.nfcore_question_style)
            if answer["all_modules"] == "All modules":
                all_modules = True
            else:
                module = questionary.autocomplete(
                    "Tool name:",
                    choices=[m.module_name for m in nfcore_modules],
                    style=nf_core.utils.nfcore_question_style,
                ).ask()

        # Only lint the given module
        if module:
            if all_modules:
                raise ModuleLintException("You cannot specify a tool and request all tools to be linted.")
            local_modules = []
            nfcore_modules = [m for m in nfcore_modules if m.module_name == module]
            if len(nfcore_modules) == 0:
                raise ModuleLintException(f"Could not find the specified module: '{module}'")

        if self.repo_type == "modules":
            log.info(f"Linting modules repo: [magenta]{self.dir}")
        else:
            log.info(f"Linting pipeline: [magenta]{self.dir}")
        if module:
            log.info(f"Linting module: [magenta]{module}")

        # Check that supplied test keys exist
        bad_keys = [k for k in self.key if k not in self.lint_tests]
        if len(bad_keys) > 0:
            raise AssertionError(
                "Test name{} not recognised: '{}'".format(
                    "s" if len(bad_keys) > 1 else "",
                    "', '".join(bad_keys),
                )
            )

        # If -k supplied, only run these tests
        if self.key:
            log.info("Only running tests: '{}'".format("', '".join(self.key)))
            self.lint_tests = [k for k in self.lint_tests if k in self.key]

        # If it is a pipeline, load the lint config file
        if self.repo_type == "pipeline":
            self._load_lint_config()

            # Only continue if a lint config has been loaded
            if self.lint_config:
                for test_name in self.lint_tests:
                    if self.lint_config.get(test_name, {}) is False:
                        log.info(f"Ignoring lint test: {test_name}")
                        self.lint_tests.remove(test_name)

        # Lint local modules
        if local and len(local_modules) > 0:
            self.lint_local_modules(local_modules)

        # Lint nf-core modules
        if len(nfcore_modules) > 0:
            self.lint_nfcore_modules(nfcore_modules)

        if print_results:
            self._print_results(show_passed=show_passed)

        return {"passed": self.passed, "warned": self.warned, "failed": self.failed}

    def lint_local_modules(self, local_modules):
        """
        Lint a local module
        Only issues warnings instead of failures
        """
        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                "Linting local modules", total=len(local_modules), test_name=os.path.basename(local_modules[0])
            )

            for mod in local_modules:
                progress_bar.update(lint_progress, advance=1, test_name=os.path.basename(mod))
                mod_object = NFCoreModule(
                    module_dir=mod, base_dir=self.dir, repo_type=self.repo_type, nf_core_module=False
                )
                mod_object.main_nf = mod
                mod_object.module_name = os.path.basename(mod)
                self.lint_module(mod_object, local=True)

    def lint_nfcore_modules(self, nfcore_modules):
        """
        Lint nf-core modules
        For each nf-core module, checks for existence of the files
        - main.nf
        - meta.yml
        - functions.nf
        And verifies that their content.

        If the linting is run for modules in the central nf-core/modules repo
        (repo_type==modules), files that are relevant for module testing are
        also examined
        """

        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            lint_progress = progress_bar.add_task(
                "Linting nf-core modules", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            for mod in nfcore_modules:
                progress_bar.update(lint_progress, advance=1, test_name=mod.module_name)
                self.lint_module(mod)

    def get_installed_modules(self):
        """
        Make a list of all modules installed in this repository

        Returns a tuple of two lists, one for local modules
        and one for nf-core modules. The local modules are represented
        as direct filepaths to the module '.nf' file.
        Nf-core module are returned as file paths to the module directories.
        In case the module contains several tools, one path to each tool directory
        is returned.

        returns (local_modules, nfcore_modules)
        """
        # initialize lists
        local_modules = []
        nfcore_modules = []
        local_modules_dir = None
        nfcore_modules_dir = os.path.join(self.dir, "modules", "nf-core", "software")

        # Get local modules
        if self.repo_type == "pipeline":
            local_modules_dir = os.path.join(self.dir, "modules", "local", "process")

            # Filter local modules
            if os.path.exists(local_modules_dir):
                local_modules = os.listdir(local_modules_dir)
                local_modules = sorted([x for x in local_modules if (x.endswith(".nf") and not x == "functions.nf")])

        # nf-core/modules
        if self.repo_type == "modules":
            nfcore_modules_dir = os.path.join(self.dir, "software")

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

        # Make full (relative) file paths and create NFCoreModule objects
        local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]
        nfcore_modules = [
            NFCoreModule(os.path.join(nfcore_modules_dir, m), repo_type=self.repo_type, base_dir=self.dir)
            for m in nfcore_modules
        ]

        return local_modules, nfcore_modules

    def _print_results(self, show_passed=False):
        """Print linting results to the command line.

        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing final results")
        console = Console(force_terminal=rich_force_colors())

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

    def lint_module(self, mod, local=False):
        """Perform linting on this module"""
        # Iterate over modules and run all checks on them

        # Only check main_if in case of a local module
        if local:
            self.main_nf(mod)
            self.passed += [LintResult(mod, m[0], m[1], m[2]) for m in mod.passed]
            self.warned += [LintResult(mod, m[0], m[1], m[2]) for m in mod.warned]

        # Otherwise run all the lint tests
        else:
            for test_name in self.lint_tests:
                getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, m[0], m[1], m[2]) for m in mod.passed]
            self.warned += [LintResult(mod, m[0], m[1], m[2]) for m in mod.warned]
            self.failed += [LintResult(mod, m[0], m[1], m[2]) for m in mod.failed]

    def _load_lint_config(self):
        """Parse a pipeline lint config file.

        Look for a file called either `.nf-core-lint.yml` or
        `.nf-core-lint.yaml` in the pipeline root directory and parse it.
        (`.yml` takes precedence).

        Add parsed config to the `self.lint_config` class attribute.
        """
        config_fn = os.path.join(self.dir, ".nf-core-lint.yml")

        # Pick up the file if it's .yaml instead of .yml
        if not os.path.isfile(config_fn):
            config_fn = os.path.join(self.dir, ".nf-core-lint.yaml")

        # Load the YAML
        try:
            with open(config_fn, "r") as fh:
                self.lint_config = yaml.safe_load(fh)
        except FileNotFoundError:
            log.debug("No lint config file found: {}".format(config_fn))
