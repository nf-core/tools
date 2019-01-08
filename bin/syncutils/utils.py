import os
import requests
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
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
        for l in nfconfig_raw.splitlines():
            ul = l.decode()
            k, v = ul.split(' = ', 1)
            config[k] = v.replace("\'", "").replace("\"", "")
    return config


def create_context(config):
    """Consumes a flat Nextflow config file and will create
    a context dictionary with information for the nf-core template creation.

    Returns: A dictionary with:
        {
            'pipeline_name': '<parsed_name>'
            'pipeline_short_description': '<parsed_description>'
            'version': '<parsed_version>'
        }
    """
    context = {}
    context["pipeline_name"] = config.get("manifest.name") if config.get("manifest.name") else get_name_from_url(config.get("manifest.homePage"))
    context["pipeline_short_description"] = config.get("manifest.description")
    context["version"] = config.get("manifest.version") if config.get("manifest.version") else config.get("params.version")
    context["author"] = config.get("manifest.author") if config.get("manifest.author") else "No author provided"
    return context


def get_name_from_url(url):
    return url.split("/")[-1] if url else ""


def repos_without_template_branch(pipeline_names):
    pipelines_without_template = []
    for pipeline in pipeline_names:
        api_call = "https://api.github.com/repos/nf-core/{}/branches".format(pipeline)
        print("Fetching branch information for nf-core/{}...".format(pipeline))
        res = requests.get(api_call)
        branch_list = res.json()
        branch_names = [branch["name"] for branch in branch_list]
        if "TEMPLATE" not in branch_names:
            pipelines_without_template.append(pipeline)
            print("WARNING: nf-core/{} had no TEMPLATE branch!".format(pipeline))

    return pipelines_without_template

