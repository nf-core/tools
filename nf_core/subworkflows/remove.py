import logging

from nf_core.components.remove import ComponentRemove

log = logging.getLogger(__name__)


class SubworkflowRemove(ComponentRemove):
    def __init__(self, pipeline_dir):
        super().__init__("subworkflows", pipeline_dir)
