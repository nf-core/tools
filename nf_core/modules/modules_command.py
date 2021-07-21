from posixpath import dirname
from nf_core import modules
import os
import glob
import shutil
import json
import logging
import yaml

import nf_core.modules.module_utils
from nf_core.modules.modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleCommand:
    """
    Base class for the 'nf-core modules' commands
    """

    def __init__(self, dir):
        """
        Initialise the ModulesCommand object
        """
        self.modules_repo = ModulesRepo()
        self.dir = dir
        self.module_names = []
        try:
            if self.dir:
                self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
            else:
                self.repo_type = None
        except LookupError as e:
            raise UserWarning(e)

        if self.repo_type == "pipeline":
            try:
                nf_core.modules.module_utils.verify_pipeline_dir(self.dir)
            except UserWarning:
                raise

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
            log.error("Could not find pipeline: {}".format(self.dir))
            return False
        main_nf = os.path.join(self.dir, "main.nf")
        nf_config = os.path.join(self.dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            raise UserWarning(f"Could not find a 'main.nf' or 'nextflow.config' file in '{self.dir}'")
        try:
            self.has_modules_file()
            return True
        except UserWarning as e:
            raise

    def has_modules_file(self):
        """Checks whether a module.json file has been created and creates one if it is missing"""
        modules_json_path = os.path.join(self.dir, "modules.json")
        if not os.path.exists(modules_json_path):
            log.info("Creating missing 'module.json' file.")
            try:
                nf_core.modules.module_utils.create_modules_json(self.dir)
            except UserWarning as e:
                raise

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
            log.debug("Successfully removed {} module".format(module_name))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def download_module_file(self, module_name, module_version, modules_repo, install_folder, module_dir):
        """Downloads the files of a module from the remote repo"""
        files = modules_repo.get_module_file_urls(module_name, module_version)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            split_filename = filename.split("/")
            dl_filename = os.path.join(self.dir, "modules", *install_folder, *split_filename[1:])
            try:
                self.modules_repo.download_gh_file(dl_filename, api_url)
            except SystemError as e:
                log.error(e)
                return False
        log.info("Downloaded {} files to {}".format(len(files), module_dir))
        return True

    def load_modules_json(self):
        """Loads the modules.json file"""
        modules_json_path = os.path.join(self.dir, "modules.json")
        try:
            with open(modules_json_path, "r") as fh:
                modules_json = json.load(fh)
        except FileNotFoundError:
            log.error("File 'modules.json' is missing")
            modules_json = None
        return modules_json

    def update_modules_json(self, modules_json, repo_name, module_name, module_version):
        """Updates the 'module.json' file with new module info"""
        if repo_name not in modules_json["repos"]:
            modules_json["repos"][repo_name] = dict()
        modules_json["repos"][repo_name][module_name] = {"git_sha": module_version}
        self.dump_modules_json(modules_json)

    def dump_modules_json(self, modules_json):
        modules_json_path = os.path.join(self.dir, "modules.json")
        with open(modules_json_path, "w") as fh:
            json.dump(modules_json, fh, indent=4)

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
            log.debug("No lint config file found: {}".format(config_fn))
