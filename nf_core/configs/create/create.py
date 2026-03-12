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
        igenomes = self.template_config.igenomes_cachedir

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

        if igenomes:
            final_params["igenomes_base"] = igenomes

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
    
    def get_resource_strings(self, cpus, memory, hours, queue='', executor='', prefix=''):
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

        queue_str = ''
        if queue:
            queue_str = f"queue = '{queue}'"

        executor_str = ''
        if executor:
            executor_str = f"executor = '{executor}'"

        resources = [cpus_str, memory_str, time_str, queue_str, executor_str]
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
                    queue=process_resources.get('custom_process_queue', ''),
                    executor=process_resources.get('executor', ''),
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
                    queue=process_resources.get('custom_process_queue', ''),
                    executor=process_resources.get('executor', ''),
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

    def construct_executor_config_str(self):
        queue_stat_interval_str = ''
        queue_size_str = ''
        poll_interval_str = ''
        submit_rate_str = ''

        if self.template_config.queue_stat_interval:
            queue_stat_interval = float(self.template_config.queue_stat_interval)
            if queue_stat_interval.is_integer():
                queue_stat_interval = int(queue_stat_interval)
                queue_stat_interval_str = f'  queueStatInterval = {queue_stat_interval}.m'
            else:
                queue_stat_interval = int(queue_stat_interval * 60)
                queue_stat_interval_str = f'  queueStatInterval = {queue_stat_interval}.s'

        if self.template_config.queue_size:
            queue_size = int(self.template_config.queue_size)
            queue_size_str = f'  queueSize = {queue_size}'

        if self.template_config.poll_interval:
            poll_interval = float(self.template_config.poll_interval)
            if poll_interval.is_integer():
                poll_interval = int(poll_interval)
                poll_interval_str = f'  pollInterval = {poll_interval}.m'
            else:
                poll_interval = int(poll_interval * 60)
                poll_interval_str = f'  pollInterval = {poll_interval}.s'

        if self.template_config.submit_rate:
            submit_rate = int(self.template_config.submit_rate)
            submit_rate_str = f"  submitRateLimit = '{submit_rate}min'"

        executor_section = [
            queue_stat_interval_str,
            queue_size_str,
            poll_interval_str,
            submit_rate_str
        ]

        executor_section = [s for s in executor_section if s]

        executor_section = [
            'executor {',
            '\n',
            *executor_section,
            '\n',
            '}',
        ]
        executor_section_str = '\n'.join(executor_section) + '\n'
        return sub(r'\n\n\n+', '\n\n', executor_section_str)

    def construct_container_config_str(self, container_name, cache_dir):
        if not container_name:
            return []
        
        enabled_str = '  enabled = true'
        cache_dir_str = f"  cacheDir = '{cache_dir}'" if cache_dir else ''
        automount_str = '  autoMounts = true' if container_name in ['singularity', 'apptainer'] else ''

        container_section = [
            enabled_str,
            cache_dir_str,
            automount_str,
        ]

        container_section = [s for s in container_section if s]

        container_section = [
            f'{container_name}' + ' {',
            '\n',
            *container_section,
            '\n',
            '}',
        ]

        container_section_str = '\n'.join(container_section) + '\n'

        return sub(r'\n\n\n+', '\n\n', container_section_str)

    def construct_infra_process_config_str(self):
        modules_to_load = (
            self.template_config.container_system
            if self.template_config.module and self.template_config.container_system 
            else ''
        )
        if self.template_config.module_system:
            if modules_to_load:
                modules_to_load += ' '
            modules_to_load += sub(r'\s+', ':', self.template_config.module_system)
        memory_str = ''
        if self.template_config.memory:
            memory_int = int(self.template_config.memory)
            memory_str = f'memory = {memory_int}.GB'
        time_str = ''
        if self.template_config.time:
            time_h = float(self.template_config.time)
            if time_h.is_integer():
                time_h = int(time_h)
                time_str = f'{time_h}.h'
            else:
                time_m = int(time_h * 60)
                time_str = f'{time_m}.m'
        resource_limits = {
            'cpus': int(self.template_config.cpus) if self.template_config.cpus else None,
            'memory': memory_str or None,
            'time': time_str or None,
        }
        resource_limits = {k: v for k, v in resource_limits.items() if v}
        resource_limits_str = [
            f'{key}: {value}'
            for key, value in resource_limits.items()
        ]
        resource_limits_str = ', '.join(resource_limits_str)
        resource_limits_str = f'[ {resource_limits_str} ]'
        process = {
            'executor': self.template_config.scheduler or None,
            'queue': self.template_config.queue or None,
            'module': modules_to_load or None,
            'resourceLimits': resource_limits_str or None,
            'scratch': f"'{self.template_config.scratch_dir}'" if self.template_config.scratch_dir else None,
            'maxRetries': self.template_config.retries or None
        }
        process = {k: v for k, v in process.items() if v}

        process_list = [
            f'  {key} = {value}'
            for key, value in process.items()
        ]
        
        process_section = [
            'process {',
            '\n',
            *process_list,
            '\n',
            '}',
        ]

        process_section_str = '\n'.join(process_section) + '\n'

        return sub(r'\n\n\n+', '\n\n', process_section_str)
    
    def construct_infra_config_str(self):
        process_section_str = self.construct_infra_process_config_str()

        executor_section_str = self.construct_executor_config_str()
        
        container_section_str = self.construct_container_config_str(
            self.template_config.container_system,
            self.template_config.cachedir
        )

        cleanup = 'true' if self.template_config.delete_work_dir else 'false'

        unscoped_configs = [
            f'cleanup = {cleanup}'
        ]
        unscoped_configs_str = '\n'.join(unscoped_configs) + '\n'

        final_config = [
            process_section_str,
            executor_section_str,
            container_section_str,
            unscoped_configs_str,
        ]

        final_config_str = '\n\n'.join(final_config) + '\n'

        return sub(r'\n\n\n+', '\n\n', final_config_str)


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
        elif self.config_type == 'infrastructure':
            process_section_str = self.construct_infra_config_str()
        else:
            raise ValueError(f'Invalid config type: {self.config_type}')

        with open(filename, "w+") as file:
            ## Write params
            file.write(params_section_str)
            file.write(process_section_str)
