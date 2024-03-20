import json

from nf_core.configs.create.utils import CreateConfig


class ConfigCreate:
    def __init__(self, template_config: CreateConfig):
        self.template_config = template_config

    ## TODO make this into a proper function here so that the exported `dict`
    ## is an actual nf-core config
    def write_to_file(self):
        with open("file.txt", "w+") as file:
            file.write(json.dumps(dict(self.template_config)))
