import os
import subprocess

def fetch_wf_config(wf_path):
    """
    Use nextflow to retrieve the nf configuration variables from a workflow
    """
    config = dict()
    # Call `nextflow config` and pipe stderr to /dev/null
    try:
        with open(os.devnull, 'w') as devnull:
            nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', wf_path], stderr=devnull)
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
        for l in nfconfig_raw.splitlines():
            ul = l.decode()
            k, v = ul.split(' = ', 1)
            config[k] = v
    return config

def create_context(config):
    """Consumes a flat Nextflow config file and will create 
    a context dictionary with information for the nf-core template creation.

    Returns: A dictionary with: 
        {
            'pipeline_name': '<parsed_name>'
            'pipeline_short_description': '<parsed_description>'
            'new_version': '<parsed_version>'
        }
    """
    context = {}
    context["name"] = config.get("manifest.name") if config.get("manifest.name") else get_name_from_url(config.get("manifest.homePage"))
    context["description"] = config.get("manifest.description") 
    context["version"] = config.get("manifest.version") if config.get("manifest.version") else config.get("params.version")
    return context

def get_name_from_url(url):
    return url.split("/")[-1] if url else ""
