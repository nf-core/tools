"""Creates a nextflow config matching the current
nf-core organization specification.
"""

from nf_core.configs.create.utils import ConfigsCreateConfig, generate_config_entry
from re import sub


class ConfigCreate:
    def __init__(self, template_config: ConfigsCreateConfig, config_type: str):
        self.template_config = template_config
        self.config_type = config_type

    def construct_info_params(self):
        final_params = {}
        contact = self.template_config.config_profile_contact
        handle = self.template_config.config_profile_handle
        description = self.template_config.config_profile_description
        url = self.template_config.config_profile_url

        if contact:
            if handle:
                config_contact = contact + " (" + handle + ")"
            else:
                config_contact = contact
            final_params["config_profile_contact"] = config_contact
        elif handle:
            final_params["config_profile_contact"] = handle

        if description:
            final_params["config_profile_description"] = description

        if url:
            final_params["config_profile_url"] = url

        return final_params

    def construct_params_str(self):
        info_params = self.construct_info_params()

        info_params_str_list = [
            f'  {key} = "{value}"'
            for key, value in info_params.items()
            if value
        ]

        params_section = [
            'params {',
            *info_params_str_list,
            '}',
        ]

        return '\n'.join(params_section) + '\n'
    
    def get_resource_strings(self, cpus, memory, hours, minutes, seconds, prefix=''):
        cpus_int = int(cpus)
        cpus_str = f'cpus = {cpus_int}'

        memory_int = int(memory)
        memory_str = f'memory = {memory_int}.Gb'

        time_h = int(hours)
        time_m = int(minutes)
        time_s = int(seconds)
        time_str = f"time = '{time_h}h {time_m}m {time_s}s'"

        resources = [cpus_str, memory_str, time_str]
        return [
            f'{prefix}{res}'
            for res in resources
        ]
    
    def construct_process_config_str(self):
        process_config_str_list = []

        # Construct default resources
        default_resources = self.get_resource_strings(
            cpus=self.template_config.default_process_ncpus,
            memory=self.template_config.default_process_memgb,
            hours=self.template_config.default_process_hours,
            minutes=self.template_config.default_process_minutes,
            seconds=self.template_config.default_process_seconds,
            prefix='  '
        )

        # Construct named process resources
        named_resources = []
        if self.template_config.named_process_resources:
            for process_name, process_resources in self.template_config.named_process_resources.items():
                named_resources.append(
                    f"  withName: '{process_name}'" + " {"
                )
                named_resources.extend(self.get_resource_strings(
                    cpus=process_resources['custom_process_ncpus'],
                    memory=process_resources['custom_process_memgb'],
                    hours=process_resources['custom_process_hours'],
                    minutes=process_resources['custom_process_minutes'],
                    seconds=process_resources['custom_process_seconds'],
                    prefix='    '
                ))
                named_resources.append('  }')

        # Construct labelled process resources
        labelled_resources = []
        if self.template_config.labelled_process_resources:
            for process_label, process_resources in self.template_config.labelled_process_resources.items():
                labelled_resources.append(
                    f"  withLabel: '{process_label}'" + " {"
                )
                labelled_resources.extend(self.get_resource_strings(
                    cpus=process_resources['custom_process_ncpus'],
                    memory=process_resources['custom_process_memgb'],
                    hours=process_resources['custom_process_hours'],
                    minutes=process_resources['custom_process_minutes'],
                    seconds=process_resources['custom_process_seconds'],
                    prefix='    '
                ))
                labelled_resources.append('  }')

        process_section = [
            'process {',
            *default_resources,
            *named_resources,
            *labelled_resources,
            '}',
        ]

        return '\n'.join(process_section) + '\n'

    def write_to_file(self):
        ## File name option
        config_name = str(self.template_config.general_config_name).strip()
        filename = sub(r'\s+', '_', config_name) + ".conf"

        ## Collect all config entries per scope, for later checking scope needs to be written
        params_section_str = self.construct_params_str()

        if self.config_type == 'pipeline':
            process_section_str = self.construct_process_config_str()
        else:
            process_section_str = ''

        with open(filename, "w+") as file:
            ## Write params
            file.write(params_section_str)
            file.write(process_section_str)
