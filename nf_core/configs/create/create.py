import json

from nf_core.configs.create.utils import CreateConfig


class ConfigCreate:
    def __init__(self, template_config: CreateConfig):
        self.template_config = template_config

    ## TODO: pull variable and file name so it's using the parameter name -> currently the written json shows that self.template_config.general_config_name is `null`
    ## TODO: replace the json.dumping with proper self.template_config parsing and config writing function

    def write_to_file(self):
        filename = self.template_config.general_config_name + ".conf"
        with open(filename, "w+") as file:
            file.write(json.dumps(dict(self.template_config)))
