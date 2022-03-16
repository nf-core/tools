from posixpath import dirname
from nf_core import modules
import os
import glob
import shutil
import copy
import json
import logging
import yaml

import nf_core.modules.module_utils
import nf_core.utils
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
                self.dir, self.repo_type = nf_core.modules.module_utils.get_repo_type(self.dir)
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

    def modules_json_up_to_date(self):
        """
        Checks whether the modules installed in the directory
        are consistent with the entries in the 'modules.json' file and vice versa.

        If a module has an entry in the 'modules.json' file but is missing in the directory,
        we first try to reinstall the module from the remote and if that fails we remove the entry
        in 'modules.json'.

        If a module is installed but the entry in 'modules.json' is missing we iterate through
        the commit log in the remote to try to determine the SHA.
        """
        mod_json = self.load_modules_json()
        fresh_mod_json = copy.deepcopy(mod_json)
        self.get_pipeline_modules()
        missing_from_modules_json = {}

        # Iterate through all installed modules
        # and remove all entries in modules_json which
        # are present in the directory
        for repo, modules in self.module_names.items():
            if repo in mod_json["repos"]:
                for module in modules:
                    if module in mod_json["repos"][repo]:
                        mod_json["repos"][repo].pop(module)
                    else:
                        if repo not in missing_from_modules_json:
                            missing_from_modules_json[repo] = []
                        missing_from_modules_json[repo].append(module)
                if len(mod_json["repos"][repo]) == 0:
                    mod_json["repos"].pop(repo)
            else:
                missing_from_modules_json[repo] = modules

        # If there are any modules left in 'modules.json' after all  installed are removed,
        # we try to reinstall them
        if len(mod_json["repos"]) > 0:
            missing_but_in_mod_json = [
                f"'{repo}/{module}'" for repo, modules in mod_json["repos"].items() for module in modules
            ]
            log.info(
                f"Reinstalling modules found in 'modules.json' but missing from directory: {', '.join(missing_but_in_mod_json)}"
            )

            remove_from_mod_json = {}
            for repo, modules in mod_json["repos"].items():
                try:
                    modules_repo = ModulesRepo(repo=repo)
                    modules_repo.get_modules_file_tree()
                    install_folder = [modules_repo.owner, modules_repo.repo]
                except LookupError as e:
                    log.warn(f"Could not get module's file tree for '{repo}': {e}")
                    remove_from_mod_json[repo] = list(modules.keys())
                    continue

                for module, entry in modules.items():
                    sha = entry.get("git_sha")
                    if sha is None:
                        if repo not in remove_from_mod_json:
                            remove_from_mod_json[repo] = []
                        log.warn(
                            f"Could not find git SHA for module '{module}' in '{repo}' - removing from modules.json"
                        )
                        remove_from_mod_json[repo].append(module)
                        continue
                    module_dir = os.path.join(self.dir, "modules", *install_folder, module)
                    self.download_module_file(module, sha, modules_repo, install_folder, module_dir)

            # If the reinstall fails, we remove those entries in 'modules.json'
            if sum(map(len, remove_from_mod_json.values())) > 0:
                uninstallable_mods = [
                    f"'{repo}/{module}'" for repo, modules in remove_from_mod_json.items() for module in modules
                ]
                if len(uninstallable_mods) == 1:
                    log.info(f"Was unable to reinstall {uninstallable_mods[0]}. Removing 'modules.json' entry")
                else:
                    log.info(
                        f"Was unable to reinstall some modules. Removing 'modules.json' entries: {', '.join(uninstallable_mods)}"
                    )

                for repo, modules in remove_from_mod_json.items():
                    for module in modules:
                        fresh_mod_json["repos"][repo].pop(module)
                    if len(fresh_mod_json["repos"][repo]) == 0:
                        fresh_mod_json["repos"].pop(repo)

        # If some modules didn't have an entry in the 'modules.json' file
        # we try to determine the SHA from the commit log of the remote
        if sum(map(len, missing_from_modules_json.values())) > 0:

            format_missing = [
                f"'{repo}/{module}'" for repo, modules in missing_from_modules_json.items() for module in modules
            ]
            if len(format_missing) == 1:
                log.info(f"Recomputing commit SHA for module {format_missing[0]} which was missing from 'modules.json'")
            else:
                log.info(
                    f"Recomputing commit SHAs for modules which were missing from 'modules.json': {', '.join(format_missing)}"
                )
            failed_to_find_commit_sha = []
            for repo, modules in missing_from_modules_json.items():
                modules_repo = ModulesRepo(repo=repo)
                repo_path = os.path.join(self.dir, "modules", repo)
                for module in modules:
                    module_path = os.path.join(repo_path, module)
                    try:
                        correct_commit_sha = nf_core.modules.module_utils.find_correct_commit_sha(
                            module, module_path, modules_repo
                        )
                        if repo not in fresh_mod_json["repos"]:
                            fresh_mod_json["repos"][repo] = {}

                        fresh_mod_json["repos"][repo][module] = {"git_sha": correct_commit_sha}
                    except (LookupError, UserWarning) as e:
                        failed_to_find_commit_sha.append(f"'{repo}/{module}'")

            if len(failed_to_find_commit_sha) > 0:

                def _s(some_list):
                    return "" if len(some_list) == 1 else "s"

                log.info(
                    f"Could not determine 'git_sha' for module{_s(failed_to_find_commit_sha)}: {', '.join(failed_to_find_commit_sha)}."
                    f"\nPlease try to install a newer version of {'this' if len(failed_to_find_commit_sha) == 1 else 'these'} module{_s(failed_to_find_commit_sha)}."
                )

        self.dump_modules_json(fresh_mod_json)

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

    def download_module_file(self, module_name, module_version, modules_repo, install_folder, dry_run=False):
        """Downloads the files of a module from the remote repo"""
        files = modules_repo.get_module_file_urls(module_name, module_version)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            split_filename = filename.split("/")
            dl_filename = os.path.join(*install_folder, *split_filename[1:])
            try:
                self.modules_repo.download_gh_file(dl_filename, api_url)
            except (SystemError, LookupError) as e:
                log.error(e)
                return False
        if not dry_run:
            log.info("Downloaded {} files to {}".format(len(files), os.path.join(*install_folder, module_name)))
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

    def update_modules_json(self, modules_json, repo_name, module_name, module_version, write_file=True):
        """Updates the 'module.json' file with new module info"""
        if repo_name not in modules_json["repos"]:
            modules_json["repos"][repo_name] = dict()
        modules_json["repos"][repo_name][module_name] = {"git_sha": module_version}
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
