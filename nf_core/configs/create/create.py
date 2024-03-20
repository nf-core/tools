import json
import logging

from nf_core.components.create import ComponentCreate
from nf_core.configs.create.utils import CreateConfig

log = logging.getLogger(__name__)


class ConfigCreate(ComponentCreate):
    def __init__(self, template_config: CreateConfig):
        super().__init__(
            "configs",
        )
        self.template_config = template_config

    def WriteToFile(self):
        with open("file.txt", "w+") as file:
            file.write(json.dumps(self.template_config))
