import logging
import os

import questionary
import rich.prompt

import nf_core.utils

log = logging.getLogger(__name__)


def get_repo_type(dir, repo_type=None, use_prompt=True):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if dir is None or not os.path.exists(dir):
        raise UserWarning(f"Could not find directory: {dir}")

    # Try to find the root directory
    base_dir = os.path.abspath(dir)
    config_path_yml = os.path.join(base_dir, ".nf-core.yml")
    config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
    while (
        not os.path.exists(config_path_yml)
        and not os.path.exists(config_path_yaml)
        and base_dir != os.path.dirname(base_dir)
    ):
        base_dir = os.path.dirname(base_dir)
        config_path_yml = os.path.join(base_dir, ".nf-core.yml")
        config_path_yaml = os.path.join(base_dir, ".nf-core.yaml")
        # Reset dir if we found the config file (will be an absolute path)
        if os.path.exists(config_path_yml) or os.path.exists(config_path_yaml):
            dir = base_dir

    # Figure out the repository type from the .nf-core.yml config file if we can
    tools_config = nf_core.utils.load_tools_config(dir)
    repo_type = tools_config.get("repository_type", None)

    # If not set, prompt the user
    if not repo_type and use_prompt:
        log.warning("Can't find a '.nf-core.yml' file that defines 'repository_type'")
        repo_type = questionary.select(
            "Is this repository an nf-core pipeline or a fork of nf-core/modules?",
            choices=[
                {"name": "Pipeline", "value": "pipeline"},
                {"name": "nf-core/modules", "value": "modules"},
            ],
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

        # Save the choice in the config file
        log.info("To avoid this prompt in the future, add the 'repository_type' key to a root '.nf-core.yml' file.")
        if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
            with open(os.path.join(dir, ".nf-core.yml"), "a+") as fh:
                fh.write(f"repository_type: {repo_type}\n")
                log.info("Config added to '.nf-core.yml'")

    # Not set and not allowed to ask
    elif not repo_type:
        raise UserWarning("Repository type could not be established")

    # Check if it's a valid answer
    if not repo_type in ["pipeline", "modules"]:
        raise UserWarning(f"Invalid repository type: '{repo_type}'")

    # It was set on the command line, return what we were given
    return [dir, repo_type]


def prompt_component_version_sha(component_name, component_type, modules_repo, installed_sha=None):
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

    all_commits = modules_repo.get_component_git_log(component_name, component_type)
    next_page_commits = [next(all_commits, None) for _ in range(10)]
    next_page_commits = [commit for commit in next_page_commits if commit is not None]

    while git_sha == "":
        commits = next_page_commits
        next_page_commits = [next(all_commits, None) for _ in range(10)]
        next_page_commits = [commit for commit in next_page_commits if commit is not None]
        if all(commit is None for commit in next_page_commits):
            next_page_commits = None

        choices = []
        for title, sha in map(lambda commit: (commit["trunc_message"], commit["git_sha"]), commits):
            display_color = "fg:ansiblue" if sha != installed_sha else "fg:ansired"
            message = f"{title} {sha}"
            if installed_sha == sha:
                message += " (installed version)"
            commit_display = [(display_color, message), ("class:choice-default", "")]
            choices.append(questionary.Choice(title=commit_display, value=sha))
        if next_page_commits is not None:
            choices += [older_commits_choice]
        git_sha = questionary.select(
            f"Select '{component_name}' commit:", choices=choices, style=nf_core.utils.nfcore_question_style
        ).unsafe_ask()
        page_nbr += 1
    return git_sha
