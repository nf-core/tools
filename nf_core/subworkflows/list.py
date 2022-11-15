import logging

from nf_core.components.list import ComponentList

log = logging.getLogger(__name__)


class SubworkflowList(ComponentList):
    def __init__(self, pipeline_dir, remote=True, remote_url=None, branch=None, no_pull=False):
        super().__init__("subworkflows", pipeline_dir, remote, remote_url, branch, no_pull)
