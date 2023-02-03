import logging

from nf_core.components.create import ComponentCreate

log = logging.getLogger(__name__)


class SubworkflowCreate(ComponentCreate):
    def __init__(
        self,
        pipeline_dir,
        component="",
        author=None,
        process_label=None,
        has_meta=None,
        force=False,
        conda_name=None,
        conda_version=None,
        minimal=False,
    ):
        super().__init__(
            "subworkflows",
            pipeline_dir,
            component,
            author,
            process_label,
            has_meta,
            force,
            conda_name,
            conda_version,
            minimal,
        )
