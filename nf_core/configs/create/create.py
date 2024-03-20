import json

from nf_core.configs.create.utils import CreateConfig


class ConfigCreate:
    def __init__(self, template_config: CreateConfig):
        self.template_config = template_config

    def write_to_file(self):
        with open("file.txt", "w+") as file:
            file.write(json.dumps(dict(self.template_config)))
