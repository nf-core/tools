import json
import logging

import rich

import nf_core.modules.modules_utils

from .modules_command import ModuleCommand
from .modules_json import ModulesJson
from .modules_repo import ModulesRepo

log = logging.getLogger(__name__)


class ModuleList(ModuleCommand):
    def __init__(self, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        super().__init__("modules", pipeline_dir, remote, remote_url, branch, no_pull)
