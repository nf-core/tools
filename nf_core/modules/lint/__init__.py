"""
Code for linting modules in the nf-core/modules repository and
in nf-core pipelines

Command:
nf-core modules lint
"""

import logging
import os

import questionary
import rich

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.lint import ComponentLint, LintExceptionError, LintResult
from nf_core.lint_utils import console

log = logging.getLogger(__name__)


class ModuleLint(ComponentLint):
    """
    An object for linting modules either in a clone of the 'nf-core/modules'
    repository or in any nf-core pipeline directory
    """

    # Import lint functions
    from .environment_yml import environment_yml  # type: ignore[misc]
    from .main_nf import main_nf  # type: ignore[misc]
    from .meta_yml import meta_yml  # type: ignore[misc]
    from .module_changes import module_changes  # type: ignore[misc]
    from .module_deprecations import module_deprecations  # type: ignore[misc]
    from .module_patch import module_patch  # type: ignore[misc]
    from .module_tests import module_tests  # type: ignore[misc]
    from .module_todos import module_todos  # type: ignore[misc]
    from .module_version import module_version  # type: ignore[misc]

    def __init__(
        self,
        dir,
        fail_warned=False,
        remote_url=None,
        branch=None,
        no_pull=False,
        registry=None,
        hide_progress=False,
    ):
        super().__init__(
            component_type="modules",
            dir=dir,
            fail_warned=fail_warned,
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
            self.lint_modules(local_modules, registry=registry, local=True, fix_version=fix_version)

        # Lint nf-core modules
        if len(remote_modules) > 0:
            self.lint_modules(remote_modules, registry=registry, local=False, fix_version=fix_version)

        if print_results:
            self._print_results(show_passed=show_passed, sort_by=sort_by)
            self.print_summary()

    def lint_modules(self, modules, registry="quay.io", local=False, fix_version=False):
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
                self.lint_module(mod, progress_bar, registry=registry, local=local, fix_version=fix_version)

    def lint_module(self, mod, progress_bar, registry, local=False, fix_version=False):
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
            if self.repo_type == "pipeline" and self.modules_json:
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
