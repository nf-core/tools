import glob
import json
import logging
import os
import re
import subprocess

import jinja2
import rich

import nf_core.utils

log = logging.getLogger(__name__)


def render_template(component_type, object_attrs, file_paths):
    """
    Create new module/subworkflow files with Jinja2.
    """
    # Run jinja2 for each file in the template folder
    env = jinja2.Environment(
        loader=jinja2.PackageLoader("nf_core", f"{component_type[:-1]}-template"), keep_trailing_newline=True
    )
    for template_fn, dest_fn in file_paths.items():
        log.debug(f"Rendering template file: '{template_fn}'")
        j_template = env.get_template(template_fn)
        object_attrs["nf_core_version"] = nf_core.__version__
        rendered_output = j_template.render(object_attrs)

        # Write output to the target file
        os.makedirs(os.path.dirname(dest_fn), exist_ok=True)
        with open(dest_fn, "w") as fh:
            log.debug(f"Writing output to: '{dest_fn}'")
            fh.write(rendered_output)

        # Mirror file permissions
        template_stat = os.stat(
            os.path.join(os.path.dirname(nf_core.__file__), f"{component_type[:-1]}-template", template_fn)
        )
        os.chmod(dest_fn, template_stat.st_mode)


def collect_name_prompt(name, component_type):
    """
    Collect module/subworkflow info via prompt if empty or invalid
    """
    # Collect module info via prompt if empty or invalid
    subname = None
    if component_type == "modules":
        pattern = r"[^a-z\d/]"
    elif component_type == "subworkflows":
        pattern = r"[^a-z\d_/]"
    if name is None:
        name = ""
    while name == "" or re.search(pattern, name) or name.count("/") > 0:
        # Check + auto-fix for invalid chacters
        if re.search(pattern, name):
            if component_type == "modules":
                log.warning("Tool/subtool name must be lower-case letters only, with no punctuation")
            elif component_type == "subworkflows":
                log.warning("Subworkflow name must be lower-case letters only, with no punctuation")
            name_clean = re.sub(r"[^a-z\d/]", "", name.lower())
            if rich.prompt.Confirm.ask(f"[violet]Change '{name}' to '{name_clean}'?"):
                name = name_clean
            else:
                name = ""

        if component_type == "modules":
            # Split into tool and subtool
            if name.count("/") > 1:
                log.warning("Tool/subtool can have maximum one '/' character")
                name = ""
            elif name.count("/") == 1:
                name, subname = name.split("/")
            else:
                subname = None  # Reset edge case: entered '/subtool' as name and gone round loop again

        # Prompt for new entry if we reset
        if name == "":
            if component_type == "modules":
                name = rich.prompt.Prompt.ask("[violet]Name of tool/subtool").strip()
            elif component_type == "subworkflows":
                name = rich.prompt.Prompt.ask("[violet]Name of subworkflow").strip()

    if component_type == "modules":
        return name, subname
    elif component_type == "subworkflows":
        return name


def get_component_dirs(component_type, repo_type, directory, org, name, supername, subname, new_dir, force_overwrite):
    """Given a directory and a tool/subtool or subworkflow, set the file paths and check if they already exist

    Returns dict: keys are relative paths to template files, vals are target paths.
    """
    file_paths = {}
    if repo_type == "pipeline":
        local_component_dir = os.path.join(directory, component_type, "local")
        # Check whether component file already exists
        component_file = os.path.join(local_component_dir, f"{name}.nf")
        if os.path.exists(component_file) and not force_overwrite:
            raise UserWarning(
                f"{component_type[:-1].title()} file exists already: '{component_file}'. Use '--force' to overwrite"
            )

        if component_type == "modules":
            # If a subtool, check if there is a module called the base tool name already
            if subname and os.path.exists(os.path.join(local_component_dir, f"{supername}.nf")):
                raise UserWarning(f"Module '{supername}' exists already, cannot make subtool '{name}'")

            # If no subtool, check that there isn't already a tool/subtool
            tool_glob = glob.glob(f"{local_component_dir}/{supername}_*.nf")
            if not subname and tool_glob:
                raise UserWarning(f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{name}'")

        # Set file paths
        file_paths[os.path.join(component_type, "main.nf")] = component_file

    if repo_type == "modules":
        software_dir = os.path.join(directory, component_type, org, new_dir)
        test_dir = os.path.join(directory, "tests", component_type, org, new_dir)

        # Check if module/subworkflow directories exist already
        if os.path.exists(software_dir) and not force_overwrite:
            raise UserWarning(f"{component_type[:-1]} directory exists: '{software_dir}'. Use '--force' to overwrite")
        if os.path.exists(test_dir) and not force_overwrite:
            raise UserWarning(f"{component_type[:-1]} test directory exists: '{test_dir}'. Use '--force' to overwrite")

        if component_type == "modules":
            # If a subtool, check if there is a module called the base tool name already
            parent_tool_main_nf = os.path.join(directory, component_type, org, supername, "main.nf")
            parent_tool_test_nf = os.path.join(directory, component_type, org, supername, "main.nf")
            if subname and os.path.exists(parent_tool_main_nf):
                raise UserWarning(f"Module '{parent_tool_main_nf}' exists already, cannot make subtool '{name}'")
            if subname and os.path.exists(parent_tool_test_nf):
                raise UserWarning(f"Module '{parent_tool_test_nf}' exists already, cannot make subtool '{name}'")

            # If no subtool, check that there isn't already a tool/subtool
            tool_glob = glob.glob(f"{os.path.join(directory, component_type, org, supername)}/*/main.nf")
            if not subname and tool_glob:
                raise UserWarning(f"Module subtool '{tool_glob[0]}' exists already, cannot make tool '{name}'")

        # Set file paths
        # For modules - can be tool/ or tool/subtool/ so can't do in template directory structure
        file_paths[os.path.join(component_type, "main.nf")] = os.path.join(software_dir, "main.nf")
        file_paths[os.path.join(component_type, "meta.yml")] = os.path.join(software_dir, "meta.yml")
        file_paths[os.path.join("tests", "main.nf")] = os.path.join(test_dir, "main.nf")
        file_paths[os.path.join("tests", "test.yml")] = os.path.join(test_dir, "test.yml")
        file_paths[os.path.join("tests", "nextflow.config")] = os.path.join(test_dir, "nextflow.config")

    return file_paths


def get_username(author):
    """
    Prompt for GitHub username
    """
    # Try to guess the current user if `gh` is installed
    author_default = None
    try:
        with open(os.devnull, "w") as devnull:
            gh_auth_user = json.loads(subprocess.check_output(["gh", "api", "/user"], stderr=devnull))
        author_default = f"@{gh_auth_user['login']}"
    except Exception as e:
        log.debug(f"Could not find GitHub username using 'gh' cli command: [red]{e}")

    # Regex to valid GitHub username: https://github.com/shinnn/github-username-regex
    github_username_regex = re.compile(r"^@[a-zA-Z\d](?:[a-zA-Z\d]|-(?=[a-zA-Z\d])){0,38}$")
    while author is None or not github_username_regex.match(author):
        if author is not None and not github_username_regex.match(author):
            log.warning("Does not look like a valid GitHub username (must start with an '@')!")
        author = rich.prompt.Prompt.ask(
            f"[violet]GitHub Username:[/]{' (@author)' if author_default is None else ''}",
            default=author_default,
        )
