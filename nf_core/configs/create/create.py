import logging

from nf_core.components.create import ComponentCreate

log = logging.getLogger(__name__)


class ConfigCreate(ComponentCreate):
    def __init__(
        self,
    ):
        super().__init__(
            "configs",
        )
