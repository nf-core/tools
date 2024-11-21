import logging

from nf_core.components.list import ComponentList

log = logging.getLogger(__name__)


class ModuleList(ComponentList):
    def __init__(self, **kwargs) -> None:
        super().__init__("modules", **kwargs)
