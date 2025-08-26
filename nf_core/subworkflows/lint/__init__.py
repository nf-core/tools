"""
Code for linting subworkflows in the nf-core/subworkflows repository and
in nf-core pipelines

Command:
nf-core subworkflows lint
"""

import logging
import os

import questionary
import rich
import ruamel.yaml

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.lint import ComponentLint, LintExceptionError, LintResult
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.pipelines.lint_utils import console, run_prettier_on_file

log = logging.getLogger(__name__)

# Import lint functions
from .main_nf import main_nf  # type: ignore[misc]
from .meta_yml import meta_yml  # type: ignore[misc]
from .subworkflow_changes import subworkflow_changes  # type: ignore[misc]
from .subworkflow_if_empty_null import subworkflow_if_empty_null  # type: ignore[misc]
from .subworkflow_tests import subworkflow_tests  # type: ignore[misc]
from .subworkflow_todos import subworkflow_todos  # type: ignore[misc]
from .subworkflow_version import subworkflow_version  # type: ignore[misc]


class SubworkflowLint(ComponentLint):
    """
    An object for linting subworkflows either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    main_nf = main_nf
    meta_yml = meta_yml
    subworkflow_changes = subworkflow_changes
    subworkflow_tests = subworkflow_tests
    subworkflow_todos = subworkflow_todos
    subworkflow_if_empty_null = subworkflow_if_empty_null
    subworkflow_version = subworkflow_version

    def __init__(
        self,
        directory,
        fail_warned=False,
        fix=False,
        remote_url=None,
        branch=None,
        no_pull=False,
        registry=None,
        hide_progress=False,
    ):
        super().__init__(
            component_type="subworkflows",
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
        subworkflow=None,
        registry="quay.io",
        key=(),
        all_subworkflows=False,
        print_results=True,
        show_passed=False,
        sort_by="test",
        local=False,
    ):
        """
        Lint all or one specific subworkflow

        First gets a list of all local subworkflows (in subworkflows/local/process) and all subworkflows
        installed from nf-core (in subworkflows/nf-core)

        For all nf-core subworkflows, the correct file structure is assured and important
        file content is verified. If directory subject to linting is a clone of 'nf-core/modules',
        the files necessary for testing the subworkflows are also inspected.

        For all local subworkflows, the '.nf' file is checked for some important flags, and warnings
        are issued if untypical content is found.

        :param subworkflow:     A specific subworkflow to lint
        :param print_results:   Whether to print the linting results
        :param show_passed:     Whether passed tests should be shown as well
        :param hide_progress:   Don't show progress bars

        :returns:               A SubworkflowLint object containing information of
                                the passed, warned and failed tests
        """
        # Use the base class unified lint method
        return super().lint(
            component=subworkflow,
            registry=registry,
            key=key,
            all_components=all_subworkflows,
            print_results=print_results,
            show_passed=show_passed,
            sort_by=sort_by,
            local=local,
            fix_version=False,  # Subworkflows don't support fix_version
        )

    def lint_subworkflows(self, subworkflows, registry="quay.io", local=False):
        """
        Lint a list of subworkflows (alias to base class method for backward compatibility)
        """
        return self.lint_components(subworkflows, registry=registry, local=local, fix_version=False)

    def lint_subworkflow(self, swf, progress_bar, registry="quay.io", local=False):
        """
        Perform linting on one subworkflow (alias to base class method for backward compatibility)
        """
        return self.lint_component(swf, progress_bar, local=local, fix_version=False, registry=registry)

    def _lint_local_component(self, component: NFCoreComponent, **kwargs):
        """Lint a local subworkflow"""
        self._is_local_linting = True

        self.main_nf(component)
        self.meta_yml(component, allow_missing=True)
        self.subworkflow_todos(component)

    def _lint_remote_component(self, component: NFCoreComponent, **kwargs):
        """Lint a remote/nf-core subworkflow"""
        self._is_local_linting = False

        # Update meta.yml file if requested
        if self.fix:
            self.update_meta_yml_file(component)

        if self.repo_type == "pipeline" and self.modules_json:
            # Set correct sha
            version = self.modules_json.get_subworkflow_version(
                component.component_name, component.repo_url, component.org
            )
            component.git_sha = version

        for test_name in self.lint_tests:
            getattr(self, test_name)(component)

    def update_meta_yml_file(self, swf):
        """
        Update the meta.yml file with the correct inputs and outputs
        """
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)

        # Read meta.yml
        with open(swf.meta_yml) as fh:
            meta_yaml = yaml.load(fh)
        meta_yaml_corrected = meta_yaml.copy()
        # Obtain inputs and outputs from main.nf
        swf.get_inputs_from_main_nf()
        swf.get_outputs_from_main_nf()

        # Compare inputs and add them if missing
        if "input" in meta_yaml:
            # Delete inputs from meta.yml which are not present in main.nf
            meta_yaml_corrected["input"] = [
                input for input in meta_yaml["input"] if list(input.keys())[0] in swf.inputs
            ]
            # Obtain inputs from main.nf missing in meta.yml
            inputs_correct = [
                list(input.keys())[0] for input in meta_yaml_corrected["input"] if list(input.keys())[0] in swf.inputs
            ]
            inputs_missing = [input for input in swf.inputs if input not in inputs_correct]
            # Add missing inputs to meta.yml
            for missing_input in inputs_missing:
                meta_yaml_corrected["input"].append({missing_input: {"description": ""}})

        if "output" in meta_yaml:
            # Delete outputs from meta.yml which are not present in main.nf
            meta_yaml_corrected["output"] = [
                output for output in meta_yaml["output"] if list(output.keys())[0] in swf.outputs
            ]
            # Obtain output from main.nf missing in meta.yml
            outputs_correct = [
                list(output.keys())[0]
                for output in meta_yaml_corrected["output"]
                if list(output.keys())[0] in swf.outputs
            ]
            outputs_missing = [output for output in swf.outputs if output not in outputs_correct]
            # Add missing inputs to meta.yml
            for missing_output in outputs_missing:
                meta_yaml_corrected["output"].append({missing_output: {"description": ""}})

        # Write corrected meta.yml to file
        with open(swf.meta_yml, "w") as fh:
            log.info(f"Updating {swf.meta_yml}")
            yaml.dump(meta_yaml_corrected, fh)
            run_prettier_on_file(fh.name)
