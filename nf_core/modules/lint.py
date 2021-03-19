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

log = logging.getLogger(__name__)


class ModuleLintException(Exception):
    """Exception raised when there was an error with module linting"""

    pass


class LintResult(object):
    """ An object to hold the results of a lint test """

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

    def __init__(self, dir):
        self.dir = dir
        self.repo_type = self.get_repo_type()
        self.passed = []
        self.warned = []
        self.failed = []

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

        # Lint local modules
        if local and len(local_modules) > 0:
            self.lint_local_modules(local_modules)

        # Lint nf-core modules
        if len(nfcore_modules) > 0:
            self.lint_nfcore_modules(nfcore_modules)

            self.check_module_changes(nfcore_modules)

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
                mod_object.lint_main_nf()
                self.passed += [LintResult(mod_object, m[0], m[1], m[2]) for m in mod_object.passed]
                self.warned += [LintResult(mod_object, m[0], m[1], m[2]) for m in mod_object.warned + mod_object.failed]

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
                passed, warned, failed = mod.lint()
                self.passed += [LintResult(mod, m[0], m[1], m[2]) for m in passed]
                self.warned += [LintResult(mod, m[0], m[1], m[2]) for m in warned]
                self.failed += [LintResult(mod, m[0], m[1], m[2]) for m in failed]

    def get_repo_type(self):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if self.dir is None or not os.path.exists(self.dir):
            log.error("Could not find directory: {}".format(self.dir))
            sys.exit(1)

        # Determine repository type
        if os.path.exists(os.path.join(self.dir, "main.nf")):
            return "pipeline"
        elif os.path.exists(os.path.join(self.dir, "software")):
            return "modules"
        else:
            log.error("Could not determine repository type of {}".format(self.dir))
            sys.exit(1)

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

    def check_module_changes(self, nfcore_modules):
        """
        Checks whether installed nf-core modules have changed compared to the
        original repository
        Downloads the 'main.nf', 'functions.nf' and 'meta.yml' files for every module
        and compare them to the local copies
        """
        all_modules_up_to_date = True
        files_to_check = ["main.nf", "functions.nf", "meta.yml"]

        progress_bar = rich.progress.Progress(
            "[bold blue]{task.description}",
            rich.progress.BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
        )
        with progress_bar:
            comparison_progress = progress_bar.add_task(
                "Comparing local file to remote", total=len(nfcore_modules), test_name=nfcore_modules[0].module_name
            )
            # Loop over nf-core modules
            for mod in nfcore_modules:
                progress_bar.update(comparison_progress, advance=1, test_name=mod.module_name)
                module_base_url = (
                    f"https://raw.githubusercontent.com/nf-core/modules/master/software/{mod.module_name}/"
                )

                for f in files_to_check:
                    # open local copy, continue if file not found (a failed message has already been issued in this case)
                    try:
                        local_copy = open(os.path.join(mod.module_dir, f), "r").read()
                    except FileNotFoundError as e:
                        continue

                    # Download remote copy and compare
                    url = module_base_url + f
                    r = requests.get(url=url)

                    if r.status_code != 200:
                        self.warned.append(
                            LintResult(
                                mod,
                                "check_local_copy",
                                f"Could not fetch remote copy, skipping comparison.",
                                f"{os.path.join(mod.module_dir, f)}",
                            )
                        )
                    else:
                        try:
                            remote_copy = r.content.decode("utf-8")

                            if local_copy != remote_copy:
                                all_modules_up_to_date = False
                                self.warned.append(
                                    LintResult(
                                        mod,
                                        "check_local_copy",
                                        "Local copy of module outdated",
                                        f"{os.path.join(mod.module_dir, f)}",
                                    )
                                )
                        except UnicodeDecodeError as e:
                            self.warned.append(
                                LintResult(
                                    mod,
                                    "check_local_copy",
                                    f"Could not decode file from {url}. Skipping comparison ({e})",
                                    f"{os.path.join(mod.module_dir, f)}",
                                )
                            )

        if all_modules_up_to_date:
            self.passed.append("All modules are up to date!")


class NFCoreModule(object):
    """
    A class to hold the information a bout a nf-core module
    Includes functionality for linting
    """

    def __init__(self, module_dir, repo_type, base_dir, nf_core_module=True):
        self.module_dir = module_dir
        self.repo_type = repo_type
        self.base_dir = base_dir
        self.passed = []
        self.warned = []
        self.failed = []
        self.inputs = []
        self.outputs = []
        self.has_meta = False

        if nf_core_module:
            # Initialize the important files
            self.main_nf = os.path.join(self.module_dir, "main.nf")
            self.meta_yml = os.path.join(self.module_dir, "meta.yml")
            self.function_nf = os.path.join(self.module_dir, "functions.nf")
            self.software = self.module_dir.split("software" + os.sep)[1]
            self.test_dir = os.path.join(self.base_dir, "tests", "software", self.software)
            self.test_yml = os.path.join(self.test_dir, "test.yml")
            self.test_main_nf = os.path.join(self.test_dir, "main.nf")
            self.module_name = module_dir.split("software" + os.sep)[1]

    def lint(self):
        """ Perform linting on this module """
        # Iterate over modules and run all checks on them

        # Lint the main.nf file
        self.lint_main_nf()

        # Lint the meta.yml file
        self.lint_meta_yml()

        # Lint the functions.nf file
        self.lint_functions_nf()

        # Lint the tests
        if self.repo_type == "modules":
            self.lint_module_tests()

        # Check for TODOs
        self.wf_path = self.module_dir
        module_todos = pipeline_todos(self)
        for i, warning in enumerate(module_todos["warned"]):
            self.warned.append(("module_todo", warning, module_todos["file_paths"][i]))

        return self.passed, self.warned, self.failed

    def lint_module_tests(self):
        """ Lint module tests """

        if os.path.exists(self.test_dir):
            self.passed.append(("test_dir_exists", "Test directory exists", self.test_dir))
        else:
            self.failed.append(("test_dir_exists", "Test directory is missing", self.test_dir))
            return

        # Lint the test main.nf file
        test_main_nf = os.path.join(self.test_dir, "main.nf")
        if os.path.exists(test_main_nf):
            self.passed.append(("test_main_exists", "test `main.nf` exists", self.test_main_nf))
        else:
            self.failed.append(("test_main_exists", "test `main.nf` does not exist", self.test_main_nf))

        # Lint the test.yml file
        try:
            with open(self.test_yml, "r") as fh:
                test_yml = yaml.safe_load(fh)
            self.passed.append(("test_yml_exists", "Test `test.yml` exists", self.test_yml))
        except FileNotFoundError:
            self.failed.append(("test_yml_exists", "Test `test.yml` does not exist", self.test_yml))

    def lint_meta_yml(self):
        """ Lint a meta yml file """
        required_keys = ["name", "input", "output"]
        required_keys_lists = ["intput", "output"]
        try:
            with open(self.meta_yml, "r") as fh:
                meta_yaml = yaml.safe_load(fh)
            self.passed.append(("meta_yml_exists", "Module `meta.yml` exists", self.meta_yml))
        except FileNotFoundError:
            self.failed.append(("meta_yml_exists", "Module `meta.yml` does not exist", self.meta_yml))
            return

        # Confirm that all required keys are given
        contains_required_keys = True
        all_list_children = True
        for rk in required_keys:
            if not rk in meta_yaml.keys():
                self.failed.append(("meta_required_keys", f"`{rk}` not specified", self.meta_yml))
                contains_required_keys = False
            elif not isinstance(meta_yaml[rk], list) and rk in required_keys_lists:
                self.failed.append(("meta_required_keys", f"`{rk}` is not a list", self.meta_yml))
                all_list_children = False
        if contains_required_keys:
            self.passed.append(("meta_required_keys", "`meta.yml` contains all required keys", self.meta_yml))

        # Confirm that all input and output channels are specified
        if contains_required_keys and all_list_children:
            meta_input = [list(x.keys())[0] for x in meta_yaml["input"]]
            for input in self.inputs:
                if input in meta_input:
                    self.passed.append(("meta_input", f"`{input}` specified", self.meta_yml))
                else:
                    self.failed.append(("meta_input", f"`{input}` missing in `meta.yml`", self.meta_yml))

            meta_output = [list(x.keys())[0] for x in meta_yaml["output"]]
            for output in self.outputs:
                if output in meta_output:
                    self.passed.append(("meta_output", "`{output}` specified", self.meta_yml))
                else:
                    self.failed.append(("meta_output", "`{output}` missing in `meta.yml`", self.meta_yml))

            # confirm that the name matches the process name in main.nf
            if meta_yaml["name"].upper() == self.process_name:
                self.passed.append(("meta_name", "Correct name specified in `meta.yml`", self.meta_yml))
            else:
                self.failed.append(
                    ("meta_name", "Conflicting process name between `meta.yml` and `main.nf`", self.meta_yml)
                )

    def lint_main_nf(self):
        """
        Lint a single main.nf module file
        Can also be used to lint local module files,
        in which case failures should be interpreted
        as warnings
        """
        inputs = []
        outputs = []

        # Check whether file exists and load it
        try:
            with open(self.main_nf, "r") as fh:
                lines = fh.readlines()
            self.passed.append(("main_nf_exists", "Module file exists", self.main_nf))
        except FileNotFoundError as e:
            self.failed.append(("main_nf_exists", "Module file does not exist", self.main_nf))
            return

        # Check that options are defined
        initoptions_re = re.compile(r"\s*options\s*=\s*initOptions\s*\(\s*params\.options\s*\)\s*")
        paramsoptions_re = re.compile(r"\s*params\.options\s*=\s*\[:\]\s*")
        if any(initoptions_re.match(l) for l in lines) and any(paramsoptions_re.match(l) for l in lines):
            self.passed.append(("main_nf_options", "'options' variable specified", self.main_nf))
        else:
            self.warned.append(("main_nf_options", "'options' variable not specified", self.main_nf))

        # Go through module main.nf file and switch state according to current section
        # Perform section-specific linting
        state = "module"
        process_lines = []
        script_lines = []
        for l in lines:
            if re.search("^\s*process\s*\w*\s*{", l) and state == "module":
                state = "process"
            if re.search("input\s*:", l) and state == "process":
                state = "input"
                continue
            if re.search("output\s*:", l) and state == "input":
                state = "output"
                continue
            if re.search("script\s*:", l) and state == "output":
                state = "script"
                continue

            # Perform state-specific linting checks
            if state == "process" and not self._is_empty(l):
                process_lines.append(l)
            if state == "input" and not self._is_empty(l):
                inputs += self._parse_input(l)
            if state == "output" and not self._is_empty(l):
                outputs += self._parse_output(l)
                outputs = list(set(outputs))  # remove duplicate 'meta's
            if state == "script" and not self._is_empty(l):
                script_lines.append(l)

        # Check the process definitions
        if self.check_process_section(process_lines):
            self.passed.append(("main_nf_container", "Container versions match", self.main_nf))
        else:
            self.warned.append(("main_nf_container", "Container versions do not match", self.main_nf))

        # Check the script definition
        self.check_script_section(script_lines)

        # Check whether 'meta' is emitted when given as input
        if "meta" in inputs:
            self.has_meta = True
            if "meta" in outputs:
                self.passed.append(("main_nf_meta_output", "'meta' map emitted in output channel(s)", self.main_nf))
            else:
                self.failed.append(("main_nf_meta_output", "'meta' map not emitted in output channel(s)", self.main_nf))

            # if meta is specified, it should also be used as 'saveAs ... publishId:meta.id'
            save_as = [pl for pl in process_lines if "saveAs" in pl]
            if len(save_as) > 0 and re.search("\s*publish_id\s*:\s*meta.id", save_as[0]):
                self.passed.append(("main_nf_meta_saveas", "'meta.id' specified in saveAs function", self.main_nf))
            else:
                self.failed.append(("main_nf_meta_saveas", "'meta.id' unspecificed in saveAs function", self.main_nf))

        # Check that a software version is emitted
        if "version" in outputs:
            self.passed.append(("main_nf_version_emitted", "Module emits software version", self.main_nf))
        else:
            self.warned.append(("main_nf_version_emitted", "Module does not emit software version", self.main_nf))

        return inputs, outputs

    def check_script_section(self, lines):
        """
        Lint the script section
        Checks whether 'def sotware' and 'def prefix' are defined
        """
        script = "".join(lines)

        # check for software
        if re.search("\s*def\s*software\s*=\s*getSoftwareName", script):
            self.passed.append(("main_nf_version_script", "Software version specified in script section", self.main_nf))
        else:
            self.warned.append(
                ("main_nf_version_script", "Software version unspecified in script section", self.main_nf)
            )

        # check for prefix (only if module has a meta map as input)
        if self.has_meta:
            if re.search("\s*prefix\s*=\s*options.suffix", script):
                self.passed.append(("main_nf_meta_prefix", "'prefix' specified in script section", self.main_nf))
            else:
                self.failed.append(("main_nf_meta_prefix", "'prefix' unspecified in script section", self.main_nf))

    def check_process_section(self, lines):
        """
        Lint the section of a module between the process definition
        and the 'input:' definition
        Specifically checks for correct software versions
        and containers
        """
        # Checks that build numbers of bioconda, singularity and docker container are matching
        build_id = "build"
        singularity_tag = "singularity"
        docker_tag = "docker"
        bioconda_packages = []

        # Process name should be all capital letters
        self.process_name = lines[0].split()[1]
        if all([x.upper() for x in self.process_name]):
            self.passed.append(("process_capitals", "Process name is in capital letters", self.main_nf))
        else:
            self.failed.append(("process_capitals", "Process name is not in captial letters", self.main_nf))

        # Check that process labels are correct
        correct_process_labels = ["process_low", "process_medium", "process_high", "process_long"]
        process_label = [l for l in lines if "label" in l]
        if len(process_label) > 0:
            process_label = process_label[0].split()[1].strip().strip("'").strip('"')
            if not process_label in correct_process_labels:
                self.warned.append(
                    (
                        "process_standard_label",
                        f"Process label ({process_label}) is not among standard labels: `{'`,`'.join(correct_process_labels)}`",
                        self.main_nf,
                    )
                )
            else:
                self.passed.append(("process_standard_label", "Correct process label", self.main_nf))
        else:
            self.warned.append(("process_standard_label", "Process label unspecified", self.main_nf))

        for l in lines:
            if re.search("bioconda::", l):
                bioconda_packages = [b for b in l.split() if "bioconda::" in b]
            if re.search("org/singularity", l):
                singularity_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()
            if re.search("biocontainers", l):
                docker_tag = l.split("/")[-1].replace('"', "").replace("'", "").split("--")[-1].strip()

        # Check that all bioconda packages have build numbers
        # Also check for newer versions
        for bp in bioconda_packages:
            bp = bp.strip("'").strip('"')
            # Check for correct version and newer versions
            try:
                bioconda_version = bp.split("=")[1]
                # response = _bioconda_package(bp)
                response = nf_core.utils.anaconda_package(bp)
            except LookupError as e:
                self.warned.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
            except ValueError as e:
                self.failed.append(("bioconda_version", "Conda version not specified correctly", self.main_nf))
            else:
                # Check that required version is available at all
                if bioconda_version not in response.get("versions"):
                    self.failed.append(("bioconda_version", "Conda package had unknown version: `{}`", self.main_nf))
                    continue  # No need to test for latest version, continue linting
                # Check version is latest available
                last_ver = response.get("latest_version")
                if last_ver is not None and last_ver != bioconda_version:
                    package, ver = bp.split("=", 1)
                    self.warned.append(
                        ("bioconda_latest", f"Conda update: {package} `{ver}` -> `{last_ver}`", self.main_nf)
                    )
                else:
                    self.passed.append(
                        ("bioconda_latest", "Conda package is the latest available: `{bp}`", self.main_nf)
                    )

        if docker_tag == singularity_tag:
            return True
        else:
            return False

    def lint_functions_nf(self):
        """
        Lint a functions.nf file
        Verifies that the file exists and contains all necessary functions
        """
        try:
            with open(self.function_nf, "r") as fh:
                lines = fh.readlines()
            self.passed.append(("functions_nf_exists", "'functions.nf' exists", self.function_nf))
        except FileNotFoundError as e:
            self.failed.append(("functions_nf_exists", "'functions.nf' does not exist", self.function_nf))
            return

        # Test whether all required functions are present
        required_functions = ["getSoftwareName", "initOptions", "getPathFromList", "saveFiles"]
        lines = "\n".join(lines)
        contains_all_functions = True
        for f in required_functions:
            if not "def " + f in lines:
                self.failed.append(("functions_nf_func_exist", "Function is missing: `{f}`", self.function_nf))
                contains_all_functions = False
        if contains_all_functions:
            self.passed.append(("functions_nf_func_exist", "All functions present", self.function_nf))

    def _parse_input(self, line):
        input = []
        # more than one input
        if "tuple" in line:
            line = line.replace("tuple", "")
            line = line.replace(" ", "")
            line = line.split(",")

            for elem in line:
                elem = elem.split("(")[1]
                elem = elem.replace(")", "").strip()
                input.append(elem)
        else:
            if "(" in line:
                input.append(line.split("(")[1].replace(")", ""))
            else:
                input.append(line.split()[1])
        return input

    def _parse_output(self, line):
        output = []
        if "meta" in line:
            output.append("meta")
        if not "emit" in line:
            self.failed.append(("missing_emit", f"Missing emit statement: {line.strip()}", self.main_nf))
        if "emit" in line:
            output.append(line.split("emit:")[1].strip())

        return output

    def _is_empty(self, line):
        """ Check whether a line is empty or a comment """
        empty = False
        if line.strip().startswith("//"):
            empty = True
        if line.strip().replace(" ", "") == "":
            empty = True
        return empty
