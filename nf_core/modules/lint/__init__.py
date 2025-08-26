"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union

import questionary
import rich
import rich.progress

import nf_core.components
import nf_core.components.nfcore_component
import nf_core.utils
from nf_core.components.lint import ComponentLint, LintExceptionError, LintResult
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.pipelines.lint_utils import console

log = logging.getLogger(__name__)

from .environment_yml import environment_yml
from .main_nf import main_nf
from .meta_yml import meta_yml, obtain_inputs, obtain_outputs, read_meta_yml
from .meta_yml_updater import MetaYmlUpdater
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
    obtain_inputs = obtain_inputs
    obtain_outputs = obtain_outputs
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
        # Use the base class unified lint method
        return super().lint(
            component=module,
            registry=registry,
            key=key,
            all_components=all_modules,
            print_results=print_results,
            show_passed=show_passed,
            sort_by=sort_by,
            local=local,
            fix_version=fix_version,
        )

    def lint_modules(
        self, modules: list[NFCoreComponent], registry: str = "quay.io", local: bool = False, fix_version: bool = False
    ) -> None:
        """
        Lint a list of modules (alias to base class method for backward compatibility)
        """
        return self.lint_components(modules, registry=registry, local=local, fix_version=fix_version)

    def lint_module(
        self,
        mod: NFCoreComponent,
        progress_bar,
        local: bool = False,
        fix_version: bool = False,
        registry: str = "quay.io",
    ):
        """
        Perform linting on one module (alias to base class method for backward compatibility)
        """
        return self.lint_component(mod, progress_bar, local=local, fix_version=fix_version, registry=registry)

    def _lint_local_component(self, component: NFCoreComponent, **kwargs):
        """Lint a local module"""
        self._is_local_linting = True
        fix_version = kwargs.get("fix_version", False)
        progress_bar = kwargs.get("progress_bar")

        component.get_inputs_from_main_nf()
        component.get_outputs_from_main_nf()

        # Update meta.yml file if requested
        if self.fix and component.meta_yml is not None:
            self.update_meta_yml_file(component)

        for test_name in self.lint_tests:
            if test_name in self.local_module_exclude_tests:
                continue
            if test_name == "main_nf":
                getattr(self, test_name)(component, fix_version, self.registry, progress_bar)
            elif test_name in ["meta_yml", "environment_yml"]:
                # Allow files to be missing for local
                getattr(self, test_name)(component, allow_missing=True)
            else:
                getattr(self, test_name)(component)

    def _lint_remote_component(self, component: NFCoreComponent, **kwargs):
        """Lint a remote/nf-core module"""
        self._is_local_linting = False
        fix_version = kwargs.get("fix_version", False)
        progress_bar = kwargs.get("progress_bar")

        component.get_inputs_from_main_nf()
        component.get_outputs_from_main_nf()

        # Update meta.yml file if requested
        if self.fix:
            self.update_meta_yml_file(component)

        if self.repo_type == "pipeline" and self.modules_json and component.repo_url:
            # Set correct sha
            version = self.modules_json.get_module_version(component.component_name, component.repo_url, component.org)
            component.git_sha = version

        for test_name in self.lint_tests:
            if test_name == "main_nf":
                getattr(self, test_name)(component, fix_version, self.registry, progress_bar)
            else:
                getattr(self, test_name)(component)

    def update_meta_yml_file(self, mod):
        """
        Update the meta.yml file with the correct inputs and outputs
        """
        updater = MetaYmlUpdater(mod)
        updater.update_meta_yml_file(self.read_meta_yml, self.obtain_inputs, self.obtain_outputs)
