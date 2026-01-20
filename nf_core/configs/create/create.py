"""Creates a nextflow config matching the current
nf-core organization specification.
"""

from nf_core.configs.create.utils import ConfigsCreateConfig, generate_config_entry
from re import sub


class ConfigCreate:
    def __init__(self, template_config: ConfigsCreateConfig, config_type: str, config_dir:str = '.'):
        self.template_config = template_config
        self.config_type = config_type
        self.config_dir = sub(r'/$', '', config_dir)

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
            '\n',
            *info_params_str_list,
            '\n',
            '}',
        ]

        params_section_str = '\n'.join(params_section) + '\n\n'
        return sub(r'\n\n\n+', '\n\n', params_section_str)
    
    def get_resource_strings(self, cpus, memory, hours, prefix=''):
        cpus_str = ''
        if cpus:
            cpus_int = int(cpus)
            cpus_str = f'cpus = {cpus_int}'

        memory_str = ''
        if memory:
            memory_int = int(memory)
            memory_str = f'memory = {memory_int}.GB'

        time_str = ''
        if hours:
            time_h = None
            time_m = None
            try:
                time_h = int(hours)
            except:
                try:
                    time_m = int(float(hours) * 60)
                except:
                    raise ValueError("Non-numeric value supplied for walltime value.")
            if time_m is not None and time_m % 60 == 0:
                time_h = int(time_m / 60)
            if time_h is not None:
                time_str = f"time = {time_h}.h"
            elif time_m is not None:
                time_str = f"time = {time_m}.m"
            else:
                raise ValueError("Non-numeric value supplied for walltime value.")

        resources = [cpus_str, memory_str, time_str]
        return [
            f'{prefix}{res}'
            for res in resources
            if res
        ]
    
    def construct_process_config_str(self):
        # Construct default resources
        default_resources = self.get_resource_strings(
            cpus=self.template_config.default_process_ncpus,
            memory=self.template_config.default_process_memgb,
            hours=self.template_config.default_process_hours,
            prefix='  '
        )

        # Construct named process resources
        named_resources = []
        if self.template_config.named_process_resources:
            for process_name, process_resources in self.template_config.named_process_resources.items():
                named_resource_string = self.get_resource_strings(
                    cpus=process_resources['custom_process_ncpus'],
                    memory=process_resources['custom_process_memgb'],
                    hours=process_resources['custom_process_hours'],
                    prefix='    '
                )
                if not named_resource_string:
                    continue
                named_resources.append(
                    f"  withName: '{process_name}'" + " {"
                )
                named_resources.extend(named_resource_string)
                named_resources.append('  }')
                named_resources.append('\n')

        # Construct labelled process resources
        labelled_resources = []
        if self.template_config.labelled_process_resources:
            for process_label, process_resources in self.template_config.labelled_process_resources.items():
                labelled_resource_string = self.get_resource_strings(
                    cpus=process_resources['custom_process_ncpus'],
                    memory=process_resources['custom_process_memgb'],
                    hours=process_resources['custom_process_hours'],
                    prefix='    '
                )
                if not labelled_resource_string:
                    continue
                labelled_resources.append(
                    f"  withLabel: '{process_label}'" + " {"
                )
                labelled_resources.extend(labelled_resource_string)
                labelled_resources.append('  }')
                labelled_resources.append('\n')

        process_section = [
            'process {',
            '\n',
            *default_resources,
            '\n',
            *named_resources,
            '\n',
            *labelled_resources,
            '\n',
            '}',
        ]

        process_section_str = '\n'.join(process_section) + '\n'

        return sub(r'\n\n\n+', '\n\n', process_section_str)

    def write_to_file(self):
        ## File name option
        config_name = str(self.template_config.general_config_name).strip()
        filename = sub(r'\s+', '_', config_name) + ".conf"
        filename = f'{self.config_dir}/{filename}'

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
