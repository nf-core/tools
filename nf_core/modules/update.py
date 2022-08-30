import logging
import os
import shutil
import tempfile
from pathlib import Path

import questionary

import nf_core.modules.module_utils
import nf_core.utils
from nf_core.utils import plural_es, plural_s, plural_y

from .modules_command import ModuleCommand
from .modules_differ import ModulesDiffer
from .modules_json import ModulesJson
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleUpdate(ModuleCommand):
    def __init__(
        self,
        pipeline_dir,
        force=False,
        prompt=False,
        sha=None,
        update_all=False,
        show_diff=None,
        save_diff_fn=None,
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        super().__init__(pipeline_dir, remote_url, branch, no_pull)
        self.force = force
        self.prompt = prompt
        self.sha = sha
        self.update_all = update_all
        self.show_diff = show_diff
        self.save_diff_fn = save_diff_fn
        self.module = None
        self.update_config = None
        self.modules_json = ModulesJson(self.dir)
        self.branch = branch

    def _parameter_checks(self):
        """Checks the compatibilty of the supplied parameters.

        Raises:
            UserWarning: if any checks fail.
        """

        if self.save_diff_fn and self.show_diff:
            raise UserWarning("Either `--preview` or `--save_diff` can be specified, not both.")

        if self.update_all and self.module:
            raise UserWarning("Either a module or the '--all' flag can be specified, not both.")

        if self.repo_type == "modules":
            raise UserWarning("Modules in clones of nf-core/modules can not be updated.")

        if self.prompt and self.sha is not None:
            raise UserWarning("Cannot use '--sha' and '--prompt' at the same time.")

        if not self.has_valid_directory():
            raise UserWarning("The command was not run in a valid pipeline directory.")

    def update(self, module=None):
        """Updates a specified module or all modules modules in a pipeline.

        Args:
            module (str): The name of the module to update.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        self.module = module

        tool_config = nf_core.utils.load_tools_config(self.dir)
        self.update_config = tool_config.get("update", {})

        self._parameter_checks()

        # Verify that 'modules.json' is consistent with the installed modules
        self.modules_json.check_up_to_date()

        if not self.update_all and module is None:
            choices = ["All modules", "Named module"]
            self.update_all = (
                questionary.select(
                    "Update all modules or a single named module?",
                    choices=choices,
                    style=nf_core.utils.nfcore_question_style,
                ).unsafe_ask()
                == "All modules"
            )

        # Verify that the provided SHA exists in the repo
        if self.sha is not None and not self.modules_repo.sha_exists_on_branch(self.sha):
            log.error(f"Commit SHA '{self.sha}' doesn't exist in '{self.modules_repo.fullname}'")
            return False

        # Get the list of modules to update, and their version information
        modules_info = self.get_all_modules_info() if self.update_all else [self.get_single_module_info(module)]

        # Save the current state of the modules.json
        old_modules_json = self.modules_json.get_modules_json()

        # Ask if we should show the diffs (unless a filename was already given on the command line)
        if not self.save_diff_fn and self.show_diff is None:
            diff_type = questionary.select(
                "Do you want to view diffs of the proposed changes?",
                choices=[
                    {"name": "No previews, just update everything", "value": 0},
                    {"name": "Preview diff in terminal, choose whether to update files", "value": 1},
                    {"name": "Just write diffs to a patch file", "value": 2},
                ],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

            self.show_diff = diff_type == 1
            self.save_diff_fn = diff_type == 2

        if self.save_diff_fn:  # True or a string
            self.setup_diff_file()

        # Loop through all modules to be updated
        # and do the requested action on them
        exit_value = True
        all_patches_successful = True
        for modules_repo, module, sha, patch_relpath in modules_info:
            module_fullname = str(Path(modules_repo.fullname, module))
            # Are we updating the files in place or not?
            dry_run = self.show_diff or self.save_diff_fn

            current_version = self.modules_json.get_module_version(module, modules_repo.fullname)

            # Set the temporary installation folder
            install_dir = Path(tempfile.mkdtemp())
            module_install_dir = install_dir / module

            # Compute the module directory
            module_dir = os.path.join(self.dir, "modules", modules_repo.fullname, module)

            if sha is not None:
                version = sha
            elif self.prompt:
                version = nf_core.modules.module_utils.prompt_module_version_sha(
                    module, modules_repo=modules_repo, installed_sha=current_version
                )
            else:
                version = modules_repo.get_latest_module_version(module)

            if current_version is not None and not self.force:
                if current_version == version:
                    if self.sha or self.prompt:
                        log.info(f"'{module_fullname}' is already installed at {version}")
                    else:
                        log.info(f"'{module_fullname}' is already up to date")
                    continue

            # Download module files
            if not self.install_module_files(module, version, modules_repo, install_dir):
                exit_value = False
                continue

            if patch_relpath is not None:
                patch_successful = self.try_apply_patch(
                    module, modules_repo.fullname, patch_relpath, module_dir, module_install_dir
                )
                if patch_successful:
                    log.info(f"Module '{module_fullname}' patched successfully")
                else:
                    log.warning(f"Failed to patch module '{module_fullname}'. Will proceed with unpatched files.")
                all_patches_successful &= patch_successful

            if dry_run:
                if patch_relpath is not None:
                    if patch_successful:
                        log.info("Current installation is compared against patched version in remote.")
                    else:
                        log.warning("Current installation is compared against unpatched version in remote.")
                # Compute the diffs for the module
                if self.save_diff_fn:
                    log.info(f"Writing diff file for module '{module_fullname}' to '{self.save_diff_fn}'")
                    ModulesDiffer.write_diff_file(
                        self.save_diff_fn,
                        module,
                        modules_repo.fullname,
                        module_dir,
                        module_install_dir,
                        current_version,
                        version,
                        dsp_from_dir=module_dir,
                        dsp_to_dir=module_dir,
                    )

                elif self.show_diff:
                    ModulesDiffer.print_diff(
                        module,
                        modules_repo.fullname,
                        module_dir,
                        module_install_dir,
                        current_version,
                        version,
                        dsp_from_dir=module_dir,
                        dsp_to_dir=module_dir,
                    )

                    # Ask the user if they want to install the module
                    dry_run = not questionary.confirm(
                        f"Update module '{module}'?", default=False, style=nf_core.utils.nfcore_question_style
                    ).unsafe_ask()

            if not dry_run:
                # Clear the module directory and move the installed files there
                self.move_files_from_tmp_dir(module, module_dir, install_dir, modules_repo.fullname, version)
                # Update modules.json with newly installed module
                self.modules_json.update(modules_repo, module, version)
            else:
                # Don't save to a file, just iteratively update the variable
                self.modules_json.update(modules_repo, module, version, write_file=False)

        if self.save_diff_fn:
            # Write the modules.json diff to the file
            ModulesDiffer.append_modules_json_diff(
                self.save_diff_fn,
                old_modules_json,
                self.modules_json.get_modules_json(),
                Path(self.dir, "modules.json"),
            )
            if exit_value:
                log.info(
                    f"[bold magenta italic] TIP! [/] If you are happy with the changes in '{self.save_diff_fn}', you "
                    "can apply them by running the command :point_right:"
                    f"  [bold magenta italic]git apply {self.save_diff_fn} [/]"
                )
        elif not all_patches_successful:
            log.info(f"Updates complete. Please apply failed patch{plural_es(modules_info)} manually")
        else:
            log.info("Updates complete :sparkles:")

        return exit_value

    def get_single_module_info(self, module):
        """Collects the module repository, version and sha for a module.

        Information about the module version in the '.nf-core.yml' overrides
        the '--sha' option

        Args:
            module_name (str): The name of the module to get info for.

        Returns:
            (ModulesRepo, str, str): The modules repo containing the module,
            the module name, and the module version.

        Raises:
            LookupError: If the module is not found either in the pipeline or the modules repo.
            UserWarning: If the '.nf-core.yml' entry is not valid.
        """
        # Check if there are any modules installed from the repo
        repo_name = self.modules_repo.fullname
        if repo_name not in self.modules_json.get_all_modules():
            raise LookupError(f"No modules installed from '{repo_name}'")

        if module is None:
            module = questionary.autocomplete(
                "Tool name:",
                choices=self.modules_json.get_all_modules()[repo_name],
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Check if module is installed before trying to update
        if module not in self.modules_json.get_all_modules()[repo_name]:
            raise LookupError(f"Module '{module}' is not installed in pipeline and could therefore not be updated")

        # Check that the supplied name is an available module
        if module and module not in self.modules_repo.get_avail_modules():
            raise LookupError(
                f"Module '{module}' not found in list of available modules."
                f"Use the command 'nf-core modules list remote' to view available software"
            )

        sha = self.sha
        if module in self.update_config.get(self.modules_repo.fullname, {}):
            config_entry = self.update_config[self.modules_repo.fullname].get(module)
            if config_entry is not None and config_entry is not True:
                if config_entry is False:
                    raise UserWarning("Module's update entry in '.nf-core.yml' is set to False")
                if not isinstance(config_entry, str):
                    raise UserWarning("Module's update entry in '.nf-core.yml' is of wrong type")

                sha = config_entry
                if self.sha is not None:
                    log.warning(
                        f"Found entry in '.nf-core.yml' for module '{module}' "
                        "which will override version specified with '--sha'"
                    )
                else:
                    log.info(f"Found entry in '.nf-core.yml' for module '{module}'")
                log.info(f"Updating module to ({sha})")

        # Check if the update branch is the same as the installation branch
        current_branch = self.modules_json.get_module_branch(module, self.modules_repo.fullname)
        new_branch = self.modules_repo.branch
        if current_branch != new_branch:
            log.warning(
                f"You are trying to update the '{Path(self.modules_repo.fullname, module)}' module from "
                f"the '{new_branch}' branch. This module was installed from the '{current_branch}'"
            )
            switch = questionary.confirm(f"Do you want to update using the '{current_branch}' instead?").unsafe_ask()
            if switch:
                # Change the branch
                self.modules_repo.setup_branch(current_branch)

        # If there is a patch file, get its filename
        patch_fn = self.modules_json.get_patch_fn(module, self.modules_repo.fullname)

        return (self.modules_repo, module, sha, patch_fn)

    def get_all_modules_info(self, branch=None):
        """Collects the module repository, version and sha for all modules.

        Information about the module version in the '.nf-core.yml' overrides the '--sha' option.

        Returns:
            [(ModulesRepo, str, str)]: A list of tuples containing a ModulesRepo object,
            the module name, and the module version.
        """
        if branch is not None:
            use_branch = questionary.confirm(
                "'--branch' was specified. Should this branch be used to update all modules?", default=False
            )
            if not use_branch:
                branch = None
        skipped_repos = []
        skipped_modules = []
        overridden_repos = []
        overridden_modules = []
        modules_info = {}
        # Loop through all the modules in the pipeline
        # and check if they have an entry in the '.nf-core.yml' file
        for repo_name, modules in self.modules_json.get_all_modules().items():
            if repo_name not in self.update_config or self.update_config[repo_name] is True:
                modules_info[repo_name] = [
                    (module, self.sha, self.modules_json.get_module_branch(module, repo_name)) for module in modules
                ]
            elif isinstance(self.update_config[repo_name], dict):
                # If it is a dict, then there are entries for individual modules
                repo_config = self.update_config[repo_name]
                modules_info[repo_name] = []
                for module in modules:
                    if module not in repo_config or repo_config[module] is True:
                        modules_info[repo_name].append(
                            (module, self.sha, self.modules_json.get_module_branch(module, repo_name))
                        )
                    elif isinstance(repo_config[module], str):
                        # If a string is given it is the commit SHA to which we should update to
                        custom_sha = repo_config[module]
                        modules_info[repo_name].append(
                            (module, custom_sha, self.modules_json.get_module_branch(module, repo_name))
                        )
                        if self.sha is not None:
                            overridden_modules.append(module)
                    elif repo_config[module] is False:
                        # Otherwise the entry must be 'False' and we should ignore the module
                        skipped_modules.append(f"{repo_name}/{module}")
                    else:
                        raise UserWarning(f"Module '{module}' in '{repo_name}' has an invalid entry in '.nf-core.yml'")
            elif isinstance(self.update_config[repo_name], str):
                # If a string is given it is the commit SHA to which we should update to
                custom_sha = self.update_config[repo_name]
                modules_info[repo_name] = [
                    (module_name, custom_sha, self.modules_json.get_module_branch(module_name, repo_name))
                    for module_name in modules
                ]
                if self.sha is not None:
                    overridden_repos.append(repo_name)
            elif self.update_config[repo_name] is False:
                skipped_repos.append(repo_name)
            else:
                raise UserWarning(f"Repo '{repo_name}' has an invalid entry in '.nf-core.yml'")

        if skipped_repos:
            skipped_str = "', '".join(skipped_repos)
            log.info(f"Skipping modules in repositor{plural_y(skipped_repos)}: '{skipped_str}'")

        if skipped_modules:
            skipped_str = "', '".join(skipped_modules)
            log.info(f"Skipping module{plural_s(skipped_modules)}: '{skipped_str}'")

        if overridden_repos:
            overridden_str = "', '".join(overridden_repos)
            log.info(
                f"Overriding '--sha' flag for modules in repositor{plural_y(overridden_repos)} "
                f"with '.nf-core.yml' entry: '{overridden_str}'"
            )

        if overridden_modules:
            overridden_str = "', '".join(overridden_modules)
            log.info(
                f"Overriding '--sha' flag for module{plural_s(overridden_modules)} with "
                f"'.nf-core.yml' entry: '{overridden_str}'"
            )
        # Loop through modules_info and create on ModulesRepo object per remote and branch
        repos_and_branches = {}
        for repo_name, mods in modules_info.items():
            for mod, sha, mod_branch in mods:
                if branch is not None:
                    mod_branch = branch
                if (repo_name, mod_branch) not in repos_and_branches:
                    repos_and_branches[(repo_name, mod_branch)] = []
                repos_and_branches[(repo_name, mod_branch)].append((mod, sha))

        # Get the git urls from the modules.json
        modules_info = (
            (
                repo_name,
                self.modules_json.get_git_url(repo_name),
                branch,
                mods_shas,
            )
            for (repo_name, branch), mods_shas in repos_and_branches.items()
        )

        # Create ModulesRepo objects
        repo_objs_mods = []
        for repo_name, repo_url, branch, mods_shas in modules_info:
            try:
                modules_repo = ModulesRepo(remote_url=repo_url, branch=branch)
            except LookupError as e:
                log.warning(e)
                log.info(f"Skipping modules in '{repo_name}'")
            else:
                repo_objs_mods.append((modules_repo, mods_shas))

        # Flatten the list
        modules_info = [(repo, mod, sha) for repo, mods_shas in repo_objs_mods for mod, sha in mods_shas]

        # Verify that that all modules and shas exist in their respective ModulesRepo,
        # don't try to update those that don't
        i = 0
        while i < len(modules_info):
            repo, module, sha = modules_info[i]
            if not repo.module_exists(module):
                log.warning(f"Module '{module}' does not exist in '{repo.fullname}'. Skipping...")
                modules_info.pop(i)
            elif sha is not None and not repo.sha_exists_on_branch(sha):
                log.warning(
                    f"Git sha '{sha}' does not exists on the '{repo.branch}' of '{repo.fullname}'. Skipping module '{module}'"
                )
                modules_info.pop(i)
            else:
                i += 1

        # Add patch filenames to the modules that have them
        modules_info = [
            (repo, mod, sha, self.modules_json.get_patch_fn(mod, repo.fullname)) for repo, mod, sha in modules_info
        ]

        return modules_info

    def setup_diff_file(self):
        """Sets up the diff file.

        If the save diff option was chosen interactively, the user is asked to supply a name for the diff file.

        Then creates the file for saving the diff.
        """
        if self.save_diff_fn is True:
            # From questionary - no filename yet
            self.save_diff_fn = questionary.path(
                "Enter the filename: ", style=nf_core.utils.nfcore_question_style
            ).unsafe_ask()

        self.save_diff_fn = Path(self.save_diff_fn)

        # Check if filename already exists (questionary or cli)
        while self.save_diff_fn.exists():
            if questionary.confirm(f"'{self.save_diff_fn}' exists. Remove file?").unsafe_ask():
                os.remove(self.save_diff_fn)
                break
            self.save_diff_fn = questionary.path(
                "Enter a new filename: ",
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            self.save_diff_fn = Path(self.save_diff_fn)

        # This guarantees that the file exists after calling the function
        self.save_diff_fn.touch()

    def move_files_from_tmp_dir(self, module, module_dir, install_folder, repo_name, new_version):
        """Move the files from the temporary to the installation directory.

        Args:
            module (str): The module name.
            module_dir (str): The path to the module directory.
            install_folder [str]: The path to the temporary installation directory.
            modules_repo (ModulesRepo): The ModulesRepo object from which the module was installed.
            new_version (str): The version of the module that was installed.
        """
        temp_module_dir = os.path.join(install_folder, module)
        files = os.listdir(temp_module_dir)

        log.debug(f"Removing old version of module '{module}'")
        self.clear_module_dir(module, module_dir)

        os.makedirs(module_dir)
        for file in files:
            path = os.path.join(temp_module_dir, file)
            if os.path.exists(path):
                shutil.move(path, os.path.join(module_dir, file))

        log.info(f"Updating '{repo_name}/{module}'")
        log.debug(f"Updating module '{module}' to {new_version} from {repo_name}")

    def try_apply_patch(self, module, repo_name, patch_relpath, module_dir, module_install_dir):
        """
        Try applying a patch file to the new module files


        Args:
            module (str): The name of the module
            repo_name (str): The name of the repository where the module resides
            patch_relpath (Path | str): The path to patch file in the pipeline
            module_dir (Path | str): The module directory in the pipeline
            module_install_dir (Path | str): The directory where the new module
                                             file have been installed

        Returns:
            (bool): Whether the patch application was successful
        """
        module_fullname = str(Path(repo_name, module))
        log.info(f"Found patch for  module '{module_fullname}'. Trying to apply it to new files")

        patch_path = Path(self.dir / patch_relpath)
        module_relpath = Path("modules", repo_name, module)

        # Copy the installed files to a new temporary directory to save them for later use
        temp_dir = Path(tempfile.mkdtemp())
        temp_module_dir = temp_dir / module
        shutil.copytree(module_install_dir, temp_module_dir)

        try:
            new_files = ModulesDiffer.try_apply_patch(module, repo_name, patch_path, temp_module_dir)
        except LookupError:
            # Patch failed. Save the patch file by moving to the install dir
            shutil.move(patch_path, Path(module_install_dir, patch_path.relative_to(module_dir)))
            log.warning(
                f"Failed to apply patch for module '{module_fullname}'. You will have to apply the patch manually"
            )
            return False

        # Write the patched files to a temporary directory
        log.debug("Writing patched files")
        for file, new_content in new_files.items():
            fn = temp_module_dir / file
            with open(fn, "w") as fh:
                fh.writelines(new_content)

        # Create the new patch file
        log.debug("Regenerating patch file")
        ModulesDiffer.write_diff_file(
            Path(temp_module_dir, patch_path.relative_to(module_dir)),
            module,
            repo_name,
            module_install_dir,
            temp_module_dir,
            file_action="w",
            for_git=False,
            dsp_from_dir=module_relpath,
            dsp_to_dir=module_relpath,
        )

        # Move the patched files to the install dir
        log.debug("Overwriting installed files installed files  with patched files")
        shutil.rmtree(module_install_dir)
        shutil.copytree(temp_module_dir, module_install_dir)

        # Add the patch file to the modules.json file
        self.modules_json.add_patch_entry(module, repo_name, patch_relpath, write_file=True)

        return True
