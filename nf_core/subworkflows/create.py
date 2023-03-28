import logging

from nf_core.components.create import ComponentCreate

log = logging.getLogger(__name__)


class SubworkflowCreate(ComponentCreate):
    def __init__(
        self,
        pipeline_dir,
        component="",
        author=None,
        force=False,
    ):
        super().__init__(
            "subworkflows",
            pipeline_dir,
            component,
            author,
            force=force,
        )
