import logging
import os
import re
from pathlib import Path

import questionary

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.modules.install import ModuleInstall
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME

from .subworkflows_command import SubworkflowCommand

log = logging.getLogger(__name__)


class SubworkflowInstall(SubworkflowCommand):
    def __init__(
        self,
        pipeline_dir,
        force=False,
        prompt=False,
        sha=None,
        remote_url=None,
        branch=None,
        no_pull=False,
    ):
        super().__init__(pipeline_dir, remote_url, branch, no_pull)
        self.force = force
        self.prompt = prompt
        self.sha = sha

    def install(self, subworkflow, silent=False):
        if self.repo_type == "modules":
            log.error("You cannot install a subworkflow in a clone of nf-core/modules")
            return False
        # Check whether pipelines is valid
        if not self.has_valid_directory():
            return False

        # Verify that 'modules.json' is consistent with the installed modules and subworkflows
        modules_json = ModulesJson(self.dir)
        modules_json.check_up_to_date()

        if self.prompt and self.sha is not None:
            log.error("Cannot use '--sha' and '--prompt' at the same time!")
            return False

        # Verify that the provided SHA exists in the repo
        if self.sha:
            if not self.modules_repo.sha_exists_on_branch(self.sha):
                log.error(f"Commit SHA '{self.sha}' doesn't exist in '{self.modules_repo.remote_url}'")
                return False

        if subworkflow is None:
            subworkflow = questionary.autocomplete(
                "Subworkflow name:",
                choices=self.modules_repo.get_avail_components(self.component_type),
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()

        # Check that the supplied name is an available subworkflow
        if subworkflow and subworkflow not in self.modules_repo.get_avail_components(self.component_type):
            log.error(f"Subworkflow '{subworkflow}' not found in list of available subworkflows.")
            log.info("Use the command 'nf-core subworkflows list' to view available software")
            return False

        if not self.modules_repo.component_exists(subworkflow, self.component_type):
            warn_msg = f"Subworkflow '{subworkflow}' not found in remote '{self.modules_repo.remote_url}' ({self.modules_repo.branch})"
            log.warning(warn_msg)
            return False

        current_version = modules_json.get_subworkflow_version(
            subworkflow, self.modules_repo.remote_url, self.modules_repo.repo_path
        )

        # Set the install folder based on the repository name
        install_folder = os.path.join(self.dir, "subworkflows", self.modules_repo.repo_path)

        # Compute the subworkflow directory
        subworkflow_dir = os.path.join(install_folder, subworkflow)

        # Check that the subworkflow is not already installed
        if (current_version is not None and os.path.exists(subworkflow_dir)) and not self.force:
            log.info("Subworkflow is already installed.")

            self.force = questionary.confirm(
                f"Subworkflow {subworkflow} is already installed.\nDo you want to force the reinstallation of this subworkflow and all it's imported modules?",
                style=nf_core.utils.nfcore_question_style,
                default=False,
            ).unsafe_ask()

            if not self.force:
                repo_flag = (
                    "" if self.modules_repo.repo_path == NF_CORE_MODULES_NAME else f"-g {self.modules_repo.remote_url} "
                )
                branch_flag = "" if self.modules_repo.branch == "master" else f"-b {self.modules_repo.branch} "

                log.info(
                    f"To update '{subworkflow}' run 'nf-core subworkflow {repo_flag}{branch_flag}update {subworkflow}'. To force reinstallation use '--force'"
                )
                return False

        if self.sha:
            version = self.sha
        elif self.prompt:
            try:
                version = nf_core.modules.modules_utils.prompt_module_version_sha(
                    subworkflow,
                    installed_sha=current_version,
                    modules_repo=self.modules_repo,
                )
            except SystemError as e:
                log.error(e)
                return False
        else:
            # Fetch the latest commit for the subworkflow
            version = self.modules_repo.get_latest_subworkflow_version(subworkflow)

        if self.force:
            log.info(f"Removing installed version of '{self.modules_repo.repo_path}/{subworkflow}'")
            self.clear_component_dir(subworkflow, subworkflow_dir)
            for repo_url, repo_content in modules_json.modules_json["repos"].items():
                for dir, dir_subworkflow in repo_content["subworkflows"].items():
                    for name, _ in dir_subworkflow.items():
                        if name == subworkflow and dir == self.modules_repo.repo_path:
                            repo_to_remove = repo_url
                            log.info(
                                f"Removing subworkflow '{self.modules_repo.repo_path}/{subworkflow}' from repo '{repo_to_remove}' from modules.json"
                            )
                            modules_json.remove_entry(subworkflow, repo_to_remove, self.modules_repo.repo_path)
                            break

        log.info(f"{'Rei' if self.force else 'I'}nstalling '{subworkflow}'")
        log.debug(f"Installing subworkflow '{subworkflow}' at hash {version} from {self.modules_repo.remote_url}")

        # Download subworkflow files
        if not self.install_subworkflow_files(subworkflow, version, self.modules_repo, install_folder):
            return False

        # Install included modules and subworkflows
        modules_to_install, subworkflows_to_install = self.get_modules_subworkflows_to_install(subworkflow_dir)
        for s_install in subworkflows_to_install:
            self.install(s_install, silent=True)
        for m_install in modules_to_install:
            module_install = ModuleInstall(
                self.dir,
                force=self.force,
                prompt=self.prompt,
                sha=self.sha,
                remote_url=self.modules_repo.remote_url,
                branch=self.modules_repo.branch,
            )
            module_install.install(m_install, silent=True)

        if not silent:
            # Print include statement
            subworkflow_name = subworkflow.upper()
            log.info(
                f"Include statement: include {{ {subworkflow_name} }} from '.{os.path.join(install_folder, subworkflow)}/main'"
            )
            subworkflow_config = os.path.join(install_folder, subworkflow, "nextflow.config")
            if os.path.isfile(subworkflow_config):
                log.info(f"Subworkflow config include statement: includeConfig '{subworkflow_config}'")

        # Update module.json with newly installed subworkflow
        modules_json.load()
        modules_json.update_subworkflow(self.modules_repo, subworkflow, version)
        return True

    def get_modules_subworkflows_to_install(self, subworkflow_dir):
        """
        Parse the subworkflow test main.nf file to retrieve all imported modules and subworkflows.
        """
        modules = []
        subworkflows = []
        with open(Path(subworkflow_dir, "main.nf"), "r") as fh:
            for line in fh:
                regex = re.compile(
                    r"include(?: *{ *)([a-zA-Z\_0-9]*)(?: *as *)?(?:[a-zA-Z\_0-9]*)?(?: *})(?: *from *)(?:'|\")(.*)(?:'|\")"
                )
                match = regex.match(line)
                if match and len(match.groups()) == 2:
                    name, link = match.groups()
                    if link.startswith("../../../"):
                        name_split = name.lower().split("_")
                        modules.append("/".join(name_split))
                    elif link.startswith("../"):
                        subworkflows.append(name.lower())
        return modules, subworkflows
