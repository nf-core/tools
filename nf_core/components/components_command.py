import logging
import os
import shutil
from pathlib import Path

import yaml

from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import ModulesRepo
from nf_core.path_utils import NFCorePaths

from .components_utils import get_repo_type

log = logging.getLogger(__name__)


class ComponentCommand:
    """
    Base class for the 'nf-core modules' and 'nf-core subworkflows' commands
    """

    def __init__(
        self, component_type, dir, org="nf-core", remote_url=None, branch=None, no_pull=False, hide_progress=False
    ):
        """
        Initialise the ComponentClass object
        """
        self.component_type = component_type
        self.dir = dir
        self.org = org
        self.paths = NFCorePaths(dir, org)
        self.modules_repo = ModulesRepo(remote_url, branch, no_pull, hide_progress)
        self.hide_progress = hide_progress

        try:
            if self.dir:
                self.dir, self.repo_type = get_repo_type(self.dir)
            else:
                self.repo_type = None
        except LookupError as e:
            raise UserWarning(e)

    def get_local_components(self):
        """
        Get the local modules/subworkflows in a pipeline
        """
        local_component_dir = Path(self.dir, self.component_type, "local")
        return [
            str(path.relative_to(local_component_dir)) for path in local_component_dir.iterdir() if path.suffix == ".nf"
        ]

    def get_components_clone_modules(self):
        """
        Get the modules/subworkflows repository available in a clone of nf-core/modules
        """
        component_base_path = self.paths.get_component_path(self.component_type)
        return [
            str(Path(dir).relative_to(component_base_path))
            for dir, _, files in os.walk(component_base_path)
            if "main.nf" in files
        ]

    def has_valid_directory(self):
        """Check that we were given a pipeline or clone of nf-core/modules"""
        if self.repo_type == "modules":
            return True
        if self.dir is None or not os.path.exists(self.dir):
            log.error(f"Could not find directory: {self.dir}")
            return False
        main_nf = self.paths.get_main_nf()
        nf_config = self.paths.get_nf_config()
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            if Path(self.dir).resolve().parts[-1].startswith("nf-core"):
                raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
            log.warning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
        return True

    def has_modules_file(self):
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = self.paths.get_modules_json()
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            ModulesJson(self.dir).create()

    def clear_component_dir(self, component_name, component_dir):
        """Removes all files in the module/subworkflow directory"""
        try:
            shutil.rmtree(component_dir)
            if self.component_type == "modules":
                # Try cleaning up empty parent if tool/subtool and tool/ is empty
                if component_name.count("/") > 0:
                    parent_dir = os.path.dirname(component_dir)
                    try:
                        os.rmdir(parent_dir)
                    except OSError:
                        log.debug(f"Parent directory not empty: '{parent_dir}'")
                    else:
                        log.debug(f"Deleted orphan tool directory: '{parent_dir}'")
            log.debug(f"Successfully removed {component_name} {self.component_type[:-1]}")
            return True
        except OSError as e:
            log.error(f"Could not remove {self.component_type[:-1]}: {e}")
            return False

    def components_from_repo(self, install_dir):
        """
        Gets the modules/subworkflows installed from a certain repository

        Args:
            install_dir (str): The name of the directory where modules/subworkflows are installed

        Returns:
            [str]: The names of the modules/subworkflows
        """
        repo_dir = Path(self.dir, self.component_type, install_dir)
        if not repo_dir.exists():
            raise LookupError(f"Nothing installed from {install_dir} in pipeline")

        return [
            str(Path(dir_path).relative_to(repo_dir)) for dir_path, _, files in os.walk(repo_dir) if "main.nf" in files
        ]

    def install_component_files(self, component_name, component_version, modules_repo, install_dir):
        """
        Installs a module/subworkflow into the given directory

        Args:
            component_name (str): The name of the module/subworkflow
            component_version (str): Git SHA for the version of the module/subworkflow to be installed
            modules_repo (ModulesRepo): A correctly configured ModulesRepo object
            install_dir (str): The path to where the module/subworkflow should be installed (should be the 'modules/' or 'subworkflows/' dir of the pipeline)

        Returns:
            (bool): Whether the operation was successful of not
        """
        return modules_repo.install_component(component_name, install_dir, component_version, self.component_type)

    def load_lint_config(self):
        """Parse a pipeline lint config file.

        Look for a file called either `.nf-core-lint.yml` or
        `.nf-core-lint.yaml` in the pipeline root directory and parse it.
        (`.yml` takes precedence).

        Add parsed config to the `self.lint_config` class attribute.
        """
        config_fn = self.paths.get_nf_core_config_yml()

        # Pick up the file if it's .yaml instead of .yml
        if not os.path.isfile(config_fn):
            config_fn = self.paths.get_nf_core_config_yaml()

        # Load the YAML
        try:
            with open(config_fn, "r") as fh:
                self.lint_config = yaml.safe_load(fh)
        except FileNotFoundError:
            log.debug(f"No lint config file found: {config_fn}")
