"""Creates a nextflow config matching the current
nf-core organization specification.
"""

from nf_core.configs.create.utils import ConfigsCreateConfig, generate_config_entry
from re import sub
from pathlib import Path


class ConfigCreate:
    def __init__(self, template_config: ConfigsCreateConfig, config_type: str, config_dir: Path | str = Path('.')):
        self.template_config = template_config
        self.config_type = config_type
        config_dir_path = config_dir if isinstance(config_dir, Path) else Path(config_dir)
        assert not config_dir_path.is_file(), f'Error: the path "{str(config_dir_path)}" is a file.'
        # Create directory if it doesn't already exist
        config_dir_path.mkdir(parents=True, exist_ok=True)
        self.config_dir = config_dir_path

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
            time_h = float(hours)
            if time_h.is_integer():
                time_h = int(time_h)
                time_str = f"time = {time_h}.h"
            else:
                time_m = int(time_h * 60)
                time_str = f"time = {time_m}.m"

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
        config_name_clean = sub(r'\W+', '_', config_name)
        config_name_clean = sub(r'_+$', '', config_name_clean)
        filename = f'{config_name_clean}.conf'
        filename = self.config_dir / filename

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
