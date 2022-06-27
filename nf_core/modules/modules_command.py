import copy
import glob
import json
import logging
import os
import shutil
from datetime import datetime
from operator import mod

import git
import questionary
import yaml

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import (
    NF_CORE_MODULES_BASE_PATH,
    NF_CORE_MODULES_NAME,
    NF_CORE_MODULES_REMOTE,
    ModulesRepo,
)
from nf_core.utils import plural_s as _s

log = logging.getLogger(__name__)


class ModuleCommand:
    """
    Base class for the 'nf-core modules' commands
    """

    def __init__(self, dir, remote_url=None, branch=None, no_pull=False, base_path=None):
        """
        Initialise the ModulesCommand object
        """
        self.modules_repo = ModulesRepo(remote_url, branch, no_pull, base_path)
        self.dir = dir
        self.module_names = []
        try:
            if self.dir:
                self.dir, self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
            else:
                self.repo_type = None
        except LookupError as e:
            raise UserWarning(e)

    def get_pipeline_modules(self):
        """
        Get the modules installed in the current directory.

        If the current directory is a pipeline, the `module_names`
        field is set to a dictionary indexed by the different
        installation repositories in the directory. If the directory
        is a clone of nf-core/modules the filed is set to
        `{"modules": modules_in_dir}`

        """

        self.module_names = {}

        module_base_path = f"{self.dir}/modules/"

        if self.repo_type == "pipeline":
            repo_owners = (owner for owner in os.listdir(module_base_path) if owner != "local")
            repo_names = (
                f"{repo_owner}/{name}"
                for repo_owner in repo_owners
                for name in os.listdir(f"{module_base_path}/{repo_owner}")
            )
            for repo_name in repo_names:
                repo_path = os.path.join(module_base_path, repo_name)
                module_mains_path = f"{repo_path}/**/main.nf"
                module_mains = glob.glob(module_mains_path, recursive=True)
                if len(module_mains) > 0:
                    self.module_names[repo_name] = [
                        os.path.dirname(os.path.relpath(mod, repo_path)) for mod in module_mains
                    ]

        elif self.repo_type == "modules":
            module_mains_path = f"{module_base_path}/**/main.nf"
            module_mains = glob.glob(module_mains_path, recursive=True)
            self.module_names["modules"] = [
                os.path.dirname(os.path.relpath(mod, module_base_path)) for mod in module_mains
            ]
        else:
            log.error("Directory is neither a clone of nf-core/modules nor a pipeline")
            raise SystemError

    def has_valid_directory(self):
        """Check that we were given a pipeline or clone of nf-core/modules"""
        if self.repo_type == "modules":
            return True
        if self.dir is None or not os.path.exists(self.dir):
            log.error(f"Could not find pipeline: {self.dir}")
            return False
        main_nf = os.path.join(self.dir, "main.nf")
        nf_config = os.path.join(self.dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
        self.has_modules_file()
        return True

    def has_modules_file(self):
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = os.path.join(self.dir, "modules.json")
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            ModulesJson(self.dir).create_modules_json()

    def clear_module_dir(self, module_name, module_dir):
        """Removes all files in the module directory"""
        try:
            shutil.rmtree(module_dir)
            # Try cleaning up empty parent if tool/subtool and tool/ is empty
            if module_name.count("/") > 0:
                parent_dir = os.path.dirname(module_dir)
                try:
                    os.rmdir(parent_dir)
                except OSError:
                    log.debug(f"Parent directory not empty: '{parent_dir}'")
                else:
                    log.debug(f"Deleted orphan tool directory: '{parent_dir}'")
            log.debug(f"Successfully removed {module_name} module")
            return True
        except OSError as e:
            log.error(f"Could not remove module: {e}")
            return False

    def install_module_files(self, module_name, module_version, modules_repo, install_dir):
        """
        Installs a module into the given directory

        Args:
            module_name (str): The name of the module
            module_versioN (str): Git SHA for the version of the module to be installed
            modules_repo (ModulesRepo): A correctly configured ModulesRepo object
            install_dir (str): The path to where the module should be installed (should be the 'modules/' dir of the pipeline)

        Returns:
            (bool): Whether the operation was successful of not
        """
        return modules_repo.install_module(module_name, install_dir, module_version)

    def load_modules_json(self):
        """
        Loads the modules.json file

        Returns:
            (nested dict...): The parsed 'modules.json' file
        """
        modules_json_path = os.path.join(self.dir, "modules.json")
        try:
            with open(modules_json_path, "r") as fh:
                modules_json = json.load(fh)
        except FileNotFoundError:
            log.error("File 'modules.json' is missing")
            modules_json = None
        return modules_json

    def update_modules_json(self, modules_json, modules_repo, module_name, module_version, write_file=True):
        """
        Updates the 'module.json' file with new module info
        """
        repo_name = modules_repo.fullname
        remote_url = modules_repo.remote_url
        base_path = modules_repo.base_path
        if repo_name not in modules_json["repos"]:
            modules_json["repos"][repo_name] = {"modules": {}, "git_url": remote_url, "base_path": base_path}
        modules_json["repos"][repo_name]["modules"][module_name] = {"git_sha": module_version}
        # Sort the 'modules.json' repo entries
        modules_json["repos"] = nf_core.utils.sort_dictionary(modules_json["repos"])
        if write_file:
            self.dump_modules_json(modules_json)
        else:
            return modules_json

    def dump_modules_json(self, modules_json):
        """Build filename for modules.json and write to file."""
        modules_json_path = os.path.join(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)
            fh.write("\n")

    def load_lint_config(self):
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
            log.debug(f"No lint config file found: {config_fn}")
