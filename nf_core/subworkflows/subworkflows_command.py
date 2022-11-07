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
