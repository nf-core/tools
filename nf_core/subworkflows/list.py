import json
import logging

import rich

import nf_core.modules.modules_utils

# from .modules_command import ModulesRepo
from nf_core.modules.modules_repo import ModulesRepo

from .subworkflows_command import SubworkflowCommand
from nf_core.components.list import ComponentList


log = logging.getLogger(__name__)


class SubworkflowList(ComponentList):
    def __init__(self, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        super().__init__("subworkflows", pipeline_dir, remote, remote_url, branch, no_pull)
