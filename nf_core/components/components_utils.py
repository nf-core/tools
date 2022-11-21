import logging
import os
import urllib
from pathlib import Path

import questionary
import rich.prompt

import nf_core.utils

log = logging.getLogger(__name__)


def get_repo_type(directory, use_prompt=True):
    """
    Determine whether this is a pipeline repository or a clone of
    nf-core/modules
    """
    # Verify that the pipeline dir exists
    if directory is None or not Path(directory).is_dir():
        raise UserWarning(f"Could not find directory: {directory}")

    # Try to find the root directory
    base_dir = nf_core.utils.determine_base_dir(directory)

    # Figure out the repository type from the .nf-core.yml config file if we can
    config_fn, tools_config = nf_core.utils.load_tools_config(dir)
    repo_type = tools_config.get("repository_type", None)

    # If not set, prompt the user
    if not repo_type and use_prompt:
        log.warning("'repository_type' not defined in %s", config_fn.name)
        repo_type = questionary.select(
            "Is this repository an nf-core pipeline or a fork of nf-core/modules?",
            choices=[
                {"name": "Pipeline", "value": "pipeline"},
                {"name": "nf-core/modules", "value": "modules"},
            ],
            style=nf_core.utils.nfcore_question_style,
        ).unsafe_ask()

        # Save the choice in the config file
        log.info(f"To avoid this prompt in the future, add the 'repository_type' key to your {config_fn.name} file.")
        if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
            with open(config_fn, "a+") as fh:
                fh.write(f"repository_type: {repo_type}\n")
                log.info("Config added to '.nf-core.yml'")

    # Not set and not allowed to ask
    elif not repo_type:
        raise UserWarning("Repository type could not be established")

    # Check if it's a valid answer
    if not repo_type in ["pipeline", "modules"]:
        raise UserWarning(f"Invalid repository type: '{repo_type}'")

    # Check for org if modules repo
    org = None
    if repo_type == "modules":
        org = tools_config.get("org_path", None)
        if org is None:
            log.warning("Organisation path not defined in '.nf-core.yml' [key: org_path]")
            repo_type = questionary.text(
                "What is the organisation path under which modules are stored? e.g. nf-core",
                default="nf-core",
                style=nf_core.utils.nfcore_question_style,
            ).unsafe_ask()
            log.info("To avoid this prompt in the future, add the 'repository_type' key to a root '.nf-core.yml' file.")
            if rich.prompt.Confirm.ask("[bold][blue]?[/] Would you like me to add this config now?", default=True):
                with open(os.path.join(dir, ".nf-core.yml"), "a+") as fh:
                    fh.write(f"org_path: {org}\n")
                    log.info("Config added to '.nf-core.yml'")

    # It was set on the command line, return what we were given
    return [base_dir, repo_type, org]


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


def path_from_git_url(git_url):
    """
    Extracts the path from the remote URL
    See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
    """
    # Check whether we have a https or ssh url
    if git_url.startswith("https"):
        path = urllib.parse.urlparse(git_url)
        path = path.path
        # Remove the intial '/'
        path = path[1:]
        # Remove extension
        path = os.path.splitext(path)[0]
        # Remove repo name "modules"
        path = os.path.split(path)[0]
    else:
        # Remove the initial `git@``
        path = git_url.split("@")
        path = path[-1] if len(path) > 1 else path[0]
        path = urllib.parse.urlparse(path)
        path = path.path
        # Remove extension
        path = os.path.splitext(path)[0]
        # Remove repo name "modules"
        path = os.path.split(path)[0]
    return path
