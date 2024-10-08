"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

import logging
import os
from pathlib import Path
from typing import List, Optional, Union

import questionary
import rich
import rich.progress
import ruamel.yaml

import nf_core.components
import nf_core.components.nfcore_component
import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_utils import get_biotools_id
from nf_core.components.lint import ComponentLint, LintExceptionError, LintResult
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.pipelines.lint_utils import console, run_prettier_on_file

log = logging.getLogger(__name__)

from .environment_yml import environment_yml
from .main_nf import main_nf
from .meta_yml import meta_yml, obtain_correct_and_specified_inputs, obtain_correct_and_specified_outputs, read_meta_yml
from .module_changes import module_changes
from .module_deprecations import module_deprecations
from .module_patch import module_patch
from .module_tests import module_tests
from .module_todos import module_todos
from .module_version import module_version


class ModuleLint(ComponentLint):
    """
    An object for linting modules either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    # Import lint functions
    environment_yml = environment_yml
    main_nf = main_nf
    meta_yml = meta_yml
    obtain_correct_and_specified_inputs = obtain_correct_and_specified_inputs
    obtain_correct_and_specified_outputs = obtain_correct_and_specified_outputs
    read_meta_yml = read_meta_yml
    module_changes = module_changes
    module_deprecations = module_deprecations
    module_patch = module_patch
    module_tests = module_tests
    module_todos = module_todos
    module_version = module_version

    def __init__(
        self,
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
            component_type="modules",
            directory=directory,
            fail_warned=fail_warned,
            fix=fix,
            remote_url=remote_url,
            branch=branch,
            no_pull=no_pull,
            registry=registry,
            hide_progress=hide_progress,
        )

    def lint(
        self,
        module=None,
        registry="quay.io",
        key=(),
        all_modules=False,
        print_results=True,
        show_passed=False,
        sort_by="test",
        local=False,
        fix_version=False,
    ):
        """
        Lint all or one specific module

        First gets a list of all local modules (in modules/local/process) and all modules
        installed from nf-core (in modules/nf-core)

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
        # TODO: consider unifying modules and subworkflows lint() function and add it to the ComponentLint class
        # Prompt for module or all
        if module is None and not all_modules and len(self.all_remote_components) > 0:
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
                    "choices": [m.component_name for m in self.all_remote_components],
                },
            ]
            answers = questionary.unsafe_prompt(questions, style=nf_core.utils.nfcore_question_style)
            all_modules = answers["all_modules"] == "All modules"
            module = answers.get("tool_name")

        # Only lint the given module
        if module:
            if all_modules:
                raise LintExceptionError("You cannot specify a tool and request all tools to be linted.")
            local_modules = []
            remote_modules = [m for m in self.all_remote_components if m.component_name == module]
            if len(remote_modules) == 0:
                raise LintExceptionError(f"Could not find the specified module: '{module}'")
        else:
            local_modules = self.all_local_components
            remote_modules = self.all_remote_components

        if self.repo_type == "modules":
            log.info(f"Linting modules repo: [magenta]'{self.directory}'")
        else:
            log.info(f"Linting pipeline: [magenta]'{self.directory}'")
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
            self.lint_modules(local_modules, registry=registry, local=True, fix_version=fix_version)

        # Lint nf-core modules
        if len(remote_modules) > 0:
            self.lint_modules(remote_modules, registry=registry, local=False, fix_version=fix_version)

        if print_results:
            self._print_results(show_passed=show_passed, sort_by=sort_by)
            self.print_summary()

    def lint_modules(
        self, modules: List[NFCoreComponent], registry: str = "quay.io", local: bool = False, fix_version: bool = False
    ) -> None:
        """
        Lint a list of modules

        Args:
            modules ([NFCoreComponent]): A list of module objects
            registry (str): The container registry to use. Should be quay.io in most situations.
            local (boolean): Whether the list consist of local or nf-core modules
            fix_version (boolean): Fix the module version if a newer version is available
        """
        # TODO: consider unifying modules and subworkflows lint_modules() function and add it to the ComponentLint class
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
                f"Linting {'local' if local else 'nf-core'} modules",
                total=len(modules),
                test_name=modules[0].component_name,
            )

            for mod in modules:
                progress_bar.update(lint_progress, advance=1, test_name=mod.component_name)
                self.lint_module(mod, progress_bar, local=local, fix_version=fix_version)

    def lint_module(
        self,
        mod: NFCoreComponent,
        progress_bar: rich.progress.Progress,
        local: bool = False,
        fix_version: bool = False,
    ):
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
        # TODO: consider unifying modules and subworkflows lint_module() function and add it to the ComponentLint class
        # Only check the main script in case of a local module
        if local:
            self.main_nf(mod, fix_version, self.registry, progress_bar)
            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in (mod.warned + mod.failed)]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

        # Otherwise run all the lint tests
        else:
            mod.get_inputs_from_main_nf()
            mod.get_outputs_from_main_nf()
            # Update meta.yml file if requested
            if self.fix:
                self.update_meta_yml_file(mod)

            if self.repo_type == "pipeline" and self.modules_json and mod.repo_url:
                # Set correct sha
                version = self.modules_json.get_module_version(mod.component_name, mod.repo_url, mod.org)
                mod.git_sha = version

            for test_name in self.lint_tests:
                if test_name == "main_nf":
                    getattr(self, test_name)(mod, fix_version, self.registry, progress_bar)
                else:
                    getattr(self, test_name)(mod)

            self.passed += [LintResult(mod, *m) for m in mod.passed]
            warned = [LintResult(mod, *m) for m in mod.warned]
            if not self.fail_warned:
                self.warned += warned
            else:
                self.failed += warned

            self.failed += [LintResult(mod, *m) for m in mod.failed]

    def update_meta_yml_file(self, mod):
        """
        Update the meta.yml file with the correct inputs and outputs
        """
        meta_yml = self.read_meta_yml(mod)
        corrected_meta_yml = meta_yml.copy()
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)

        # Obtain inputs and outputs from main.nf and meta.yml
        # Used to compare only the structure of channels and elements
        # Do not compare features to allow for custom features in meta.yml (i.e. pattern)
        if "input" in meta_yml:
            correct_inputs, meta_inputs = self.obtain_correct_and_specified_inputs(mod, meta_yml)
        if "output" in meta_yml:
            correct_outputs, meta_outputs = self.obtain_correct_and_specified_outputs(mod, meta_yml)

        if "input" in meta_yml and correct_inputs != meta_inputs:
            log.debug(
                f"Correct inputs: '{correct_inputs}' differ from current inputs: '{meta_inputs}' in '{mod.meta_yml}'"
            )
            corrected_meta_yml["input"] = mod.inputs.copy()  # list of lists (channels) of dicts (elements)
            for i, channel in enumerate(corrected_meta_yml["input"]):
                for j, element in enumerate(channel):
                    element_name = list(element.keys())[0]
                    for k, meta_element in enumerate(meta_yml["input"]):
                        try:
                            # Handle old format of meta.yml: list of dicts (channels)
                            if element_name in meta_element.keys():
                                # Copy current features of that input element form meta.yml
                                for feature in meta_element[element_name].keys():
                                    if feature not in element[element_name].keys():
                                        corrected_meta_yml["input"][i][j][element_name][feature] = meta_element[
                                            element_name
                                        ][feature]
                                break
                        except AttributeError:
                            # Handle new format of meta.yml: list of lists (channels) of elements (dicts)
                            for x, meta_ch_element in enumerate(meta_element):
                                if element_name in meta_ch_element.keys():
                                    # Copy current features of that input element form meta.yml
                                    for feature in meta_element[x][element_name].keys():
                                        if feature not in element[element_name].keys():
                                            corrected_meta_yml["input"][i][j][element_name][feature] = meta_element[x][
                                                element_name
                                            ][feature]
                                    break

        if "output" in meta_yml and correct_outputs != meta_outputs:
            log.debug(
                f"Correct outputs: '{correct_outputs}' differ from current outputs: '{meta_outputs}' in '{mod.meta_yml}'"
            )
            corrected_meta_yml["output"] = mod.outputs.copy()  # list of dicts (channels) with list of dicts (elements)
            for i, channel in enumerate(corrected_meta_yml["output"]):
                ch_name = list(channel.keys())[0]
                for j, element in enumerate(channel[ch_name]):
                    element_name = list(element.keys())[0]
                    for k, meta_element in enumerate(meta_yml["output"]):
                        if element_name in meta_element.keys():
                            # Copy current features of that output element form meta.yml
                            for feature in meta_element[element_name].keys():
                                if feature not in element[element_name].keys():
                                    corrected_meta_yml["output"][i][ch_name][j][element_name][feature] = meta_element[
                                        element_name
                                    ][feature]
                            break
                        elif ch_name in meta_element.keys():
                            # When the previous output element was using the name of the channel
                            # Copy current features of that output element form meta.yml
                            try:
                                # Handle old format of meta.yml
                                for feature in meta_element[ch_name].keys():
                                    if feature not in element[element_name].keys():
                                        corrected_meta_yml["output"][i][ch_name][j][element_name][feature] = (
                                            meta_element[ch_name][feature]
                                        )
                            except AttributeError:
                                # Handle new format of meta.yml
                                for x, meta_ch_element in enumerate(meta_element[ch_name]):
                                    for meta_ch_element_name in meta_ch_element.keys():
                                        for feature in meta_ch_element[meta_ch_element_name].keys():
                                            if feature not in element[element_name].keys():
                                                corrected_meta_yml["output"][i][ch_name][j][element_name][feature] = (
                                                    meta_ch_element[meta_ch_element_name][feature]
                                                )
                            break

        # Add bio.tools identifier
        for i, tool in enumerate(corrected_meta_yml["tools"]):
            tool_name = list(tool.keys())[0]
            if "identifier" not in tool[tool_name]:
                corrected_meta_yml["tools"][i][tool_name]["identifier"] = get_biotools_id(
                    mod.component_name if "/" not in mod.component_name else mod.component_name.split("/")[0]
                )

        with open(mod.meta_yml, "w") as fh:
            log.info(f"Updating {mod.meta_yml}")
            yaml.dump(corrected_meta_yml, fh)
            run_prettier_on_file(fh.name)
