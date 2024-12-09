import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import questionary
import requests
import rich.prompt

if TYPE_CHECKING:
    from nf_core.modules.modules_repo import ModulesRepo

import nf_core.utils

log = logging.getLogger(__name__)

# Constants for the nf-core/modules repo used throughout the module files
NF_CORE_MODULES_NAME = "nf-core"
NF_CORE_MODULES_REMOTE = "https://github.com/nf-core/modules.git"
NF_CORE_MODULES_DEFAULT_BRANCH = "master"


def get_repo_info(directory: Path, use_prompt: Optional[bool] = True) -> Tuple[Path, Optional[str], str]:
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """

    # Verify that the pipeline dir exists
    if not Path(directory).is_dir():
        raise UserWarning(f"Could not find directory: {directory}")

    # Try to find the root directory
    base_dir: Path = nf_core.utils.determine_base_dir(directory)

    # Figure out the repository type from the .nf-core.yml config file if we can
    config_fn, tools_config = nf_core.utils.load_tools_config(base_dir)
    if config_fn is None:
        raise UserWarning(f"Could not find a config file in directory: {base_dir}")
    repo_type = getattr(tools_config, "repository_type", None) or None

    # If not set, prompt the user
    if not repo_type and use_prompt:
        log.warning("'repository_type' not defined in %s", config_fn.name)
        repo_type = questionary.select(
            "Is this repository a pipeline or a modules repository?",
            choices=[
                {"name": "Pipeline", "value": "pipeline"},
                {"name": "Modules repository", "value": "modules"},
            ],
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

        # Save the choice in the config file
        log.info(f"To avoid this prompt in the future, add the 'repository_type' key to your {config_fn.name} file.")
        if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
            with open(config_fn, "a+") as fh:
                fh.write(f"repository_type: {repo_type}\n")
                log.info(f"Config added to '{config_fn.name}'")

    # Not set and not allowed to ask
    elif not repo_type:
        raise UserWarning("Repository type could not be established")

    # Check if it's a valid answer
    if repo_type not in ["pipeline", "modules"]:
        raise UserWarning(f"Invalid repository type: '{repo_type}', must be 'pipeline' or 'modules'")
    org: str = ""
    # Check for org if modules repo
    if repo_type == "modules":
        org = getattr(tools_config, "org_path", "") or ""
        if org == "":
            log.warning("Organisation path not defined in %s [key: org_path]", config_fn.name)
            org = questionary.text(
                "What is the organisation path under which modules and subworkflows are stored?",
                default="nf-core",
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            log.info("To avoid this prompt in the future, add the 'org_path' key to a root '%s' file.", config_fn.name)
            if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
                with open(config_fn, "a+") as fh:
                    fh.write(f"org_path: {org}\n")
                    log.info(f"Config added to '{config_fn.name}'")

        if not org:
            raise UserWarning("Organisation path could not be established")

    # It was set on the command line, return what we were given
    return (base_dir, repo_type, org)


def prompt_component_version_sha(
    component_name: str,
    component_type: str,
    modules_repo: "ModulesRepo",
    installed_sha: Optional[str] = None,
) -> str:
    """
    Creates an interactive questionary prompt for selecting the module/subworkflow version
    Args:
        component_name (str): Module/subworkflow name,
        component_type (str): "modules" or "subworkflows",
        modules_repo (ModulesRepo): Modules repo the module/subworkflow originate in
        installed_sha (str): Optional extra argument to highlight the current installed version

    Returns:
        git_sha (str): The selected version of the module/subworkflow
    """
    older_commits_choice = questionary.Choice(
        title=[("fg:ansiyellow", "older commits"), ("class:choice-default", "")], value=""
    )
    git_sha = ""
    page_nbr = 1

    all_commits = iter(modules_repo.get_component_git_log(component_name, component_type))
    next_page_commits = [next(all_commits, None) for _ in range(10)]
    next_page_commits = [commit for commit in next_page_commits if commit is not None]

    while git_sha == "":
        commits = next_page_commits
        next_page_commits = [next(all_commits, None) for _ in range(10)]
        next_page_commits = [commit for commit in next_page_commits if commit is not None]
        if all(commit is None for commit in next_page_commits):
            next_page_commits = []

        choices = []
        for commit in commits:
            if commit:
                title = commit["trunc_message"]
                sha = commit["git_sha"]
                display_color = "fg:ansiblue" if sha != installed_sha else "fg:ansired"
                message = f"{title} {sha}"
                if installed_sha == sha:
                    message += " (installed version)"
                commit_display = [(display_color, message), ("class:choice-default", "")]
                choices.append(questionary.Choice(title=commit_display, value=sha))
        if next_page_commits:
            choices += [older_commits_choice]
        git_sha = questionary.select(
            f"Select '{component_name}' commit:", choices=choices, style=nf_core.utils.nfcore_question_style
        ).unsafe_ask()
        page_nbr += 1
    return git_sha


def get_components_to_install(subworkflow_dir: Union[str, Path]) -> Tuple[List[str], List[str]]:
    """
    Parse the subworkflow main.nf file to retrieve all imported modules and subworkflows.
    """
    modules = []
    subworkflows = []
    with open(Path(subworkflow_dir, "main.nf")) as fh:
        for line in fh:
            regex = re.compile(
                r"include(?: *{ *)([a-zA-Z\_0-9]*)(?: *as *)?(?:[a-zA-Z\_0-9]*)?(?: *})(?: *from *)(?:'|\")(.*)(?:'|\")"
            )
            match = regex.search(line)
            if match and len(match.groups()) == 2:
                name, link = match.groups()
                if link.startswith("../../../"):
                    name_split = name.lower().split("_")
                    modules.append("/".join(name_split))
                elif link.startswith("../"):
                    subworkflows.append(name.lower())
    return modules, subworkflows


def get_biotools_id(tool_name) -> str:
    """
    Try to find a bio.tools ID for 'tool'
    """
    url = f"https://bio.tools/api/t/?q={tool_name}&format=json"
    try:
        # Send a GET request to the API
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        # Parse the JSON response
        data = response.json()

        # Iterate through the tools in the response to find the tool name
        for tool in data["list"]:
            if tool["name"].lower() == tool_name:
                return tool["biotoolsCURIE"]

        # If the tool name was not found in the response
        log.warning(f"Could not find a bio.tools ID for '{tool_name}'")
        return ""

    except requests.exceptions.RequestException as e:
        log.warning(f"Could not find a bio.tools ID for '{tool_name}': {e}")
        return ""
