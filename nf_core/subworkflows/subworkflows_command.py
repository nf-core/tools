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

    def clear_subworkflow_dir(self, subworkflow_name, subworkflow_dir):
        """Removes all files in the subworkflow directory"""
        try:
            shutil.rmtree(subworkflow_dir)
            log.debug(f"Successfully removed {subworkflow_name} subworkflow")
            return True
        except OSError as e:
            log.error(f"Could not remove subworkflow: {e}")
            return False
