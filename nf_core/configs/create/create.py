import json

from nf_core.configs.create.utils import CreateConfig, generate_config_entry


class ConfigCreate:
    def __init__(self, template_config: CreateConfig):
        self.template_config = template_config

    def construct_contents(self):
        parsed_contents = {
            "params": {
                "config_profile_description": self.template_config.config_profile_description,
                "config_profile_contact": "Boaty McBoatFace (@BoatyMcBoatFace)",
            }
        }

        return parsed_contents

    def write_to_file(self):
        ## File name option
        filename = self.template_config.general_config_name + ".conf"

        ## Collect all config entries per scope, for later checking scope needs to be written
        validparams = {
            "config_profile_contact": self.template_config.config_profile_contact,
            "config_profile_handle": self.template_config.config_profile_handle,
            "config_profile_description": self.template_config.config_profile_description,
        }

        print(validparams)

        with open(filename, "w+") as file:

            ## Write params
            if any(validparams):
                file.write("params {\n")
                for entry_key, entry_value in validparams.items():
                    print(entry_key)
                    if entry_value is not None:
                        file.write(generate_config_entry(self, entry_key, entry_value))
                    else:
                        continue
                file.write("}\n")


# (
#                     file.write(
#                         '  config_profile_contact = "'
#                         + self.template_config.param_profilecontact
#                         + " (@"
#                         + self.template_config.param_profilecontacthandle
#                         + ')"\n'
#                     )
#                     if self.template_config.param_profilecontact
#                     else None
#                 ),
#                 (
#                     file.write(
#                         '  config_profile_description = "'
#                         + self.template_config.param_configprofiledescription
#                         + '"\n'
#                     )
#                     if self.template_config.param_configprofiledescription
#                     else None
#                 ),
