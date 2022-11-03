import logging
import os
import re
from pathlib import Path

import questionary

import nf_core.components.components_install
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

        # Verify SHA
        if not self.modules_repo.verify_sha(self.prompt, self.sha):
            return False

        # Check and verify subworkflow name
        subworkflow = nf_core.components.components_install.collect_and_verify_name(
            self.component_type, subworkflow, self.modules_repo
        )
        if not subworkflow:
            return False

        # Get current version
        current_version = modules_json.get_subworkflow_version(
            subworkflow, self.modules_repo.remote_url, self.modules_repo.repo_path
        )

        # Set the install folder based on the repository name
        install_folder = os.path.join(self.dir, "subworkflows", self.modules_repo.repo_path)

        # Compute the subworkflow directory
        subworkflow_dir = os.path.join(install_folder, subworkflow)

        # Check that the subworkflow is not already installed
        if not nf_core.components.components_install.check_component_installed(
            self.component_type, subworkflow, current_version, subworkflow_dir, self.modules_repo, self.force
        ):
            return False

        version = nf_core.components.components_install.get_version(
            subworkflow, self.component_type, self.sha, self.prompt, current_version, self.modules_repo
        )
        if not version:
            return False

        # Remove subworkflow if force is set
        if self.force:
            log.info(f"Removing installed version of '{self.modules_repo.repo_path}/{subworkflow}'")
            self.clear_component_dir(subworkflow, subworkflow_dir)
            nf_core.components.components_install.clean_modules_json(
                subworkflow, self.component_type, self.modules_repo, modules_json
            )

        log.info(f"{'Rei' if self.force else 'I'}nstalling '{subworkflow}'")
        log.debug(f"Installing subworkflow '{subworkflow}' at hash {version} from {self.modules_repo.remote_url}")

        # Download subworkflow files
        if not self.install_component_files(subworkflow, version, self.modules_repo, install_folder):
            return False

        # Install included modules and subworkflows
        self.install_included_components(subworkflow_dir)

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

    def install_included_components(self, subworkflow_dir):
        """
        Install included modules and subworkflows
        """
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
