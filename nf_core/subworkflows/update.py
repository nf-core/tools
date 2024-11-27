from nf_core.components.update import ComponentUpdate


class SubworkflowUpdate(ComponentUpdate):
    def __init__(self, pipeline_dir, **kwargs) -> None:
        super().__init__(pipeline_dir, "subworkflows", **kwargs)
