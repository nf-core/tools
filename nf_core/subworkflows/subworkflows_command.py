import logging
import os
import shutil
from pathlib import Path

from nf_core.components.components_command import ComponentCommand

log = logging.getLogger(__name__)


class SubworkflowCommand(ComponentCommand):
    """
    Base class for the 'nf-core subworkflows' commands
    """

    def __init__(self, dir, remote_url=None, branch=None, no_pull=False, hide_progress=False):
        super().__init__("subworkflows", dir, remote_url, branch, no_pull, hide_progress)

    def subworkflows_from_repo(self, install_dir):
        """
        Gets the subworkflows installed from a certain repository

        Args:
            install_dir (str): The name of the directory where subworkflows are installed

        Returns:
            [str]: The names of the subworkflows
        """
        repo_dir = Path(self.dir, "subworkflows", install_dir)
        if not repo_dir.exists():
            raise LookupError(f"Nothing installed from {install_dir} in pipeline")

        return [
            str(Path(dir_path).relative_to(repo_dir)) for dir_path, _, files in os.walk(repo_dir) if "main.nf" in files
        ]

    def install_subworkflow_files(self, subworkflow_name, subworkflow_version, modules_repo, install_dir):
        """
        Installs a subworkflow into the given directory

        Args:
            subworkflow_name (str): The name of the subworkflow
            subworkflow_version (str): Git SHA for the version of the subworkflow to be installed
            modules_repo (ModulesRepo): A correctly configured ModulesRepo object
            install_dir (str): The path to where the subworkflow should be installed (should be the 'subworkflow/' dir of the pipeline)

        Returns:
            (bool): Whether the operation was successful of not
        """
        return modules_repo.install_subworkflow(subworkflow_name, install_dir, subworkflow_version)

    def clear_subworkflow_dir(self, subworkflow_name, subworkflow_dir):
        """Removes all files in the subworkflow directory"""
        try:
            shutil.rmtree(subworkflow_dir)
            log.debug(f"Successfully removed {subworkflow_name} subworkflow")
            return True
        except OSError as e:
            log.error(f"Could not remove subworkflow: {e}")
            return False
