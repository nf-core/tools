import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from ..components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


class ModuleExceptionError(Exception):
    """Exception raised when there was an error with module commands"""

    pass


def get_container_with_regex(main_nf_path: Path, component_name: str | None = None) -> str:
    """
    Extract the container directive from a main.nf file using regex.

    Args:
        main_nf_path: Path to the main.nf file
        component_name: Optional component name for logging

    Returns:
        str: The container string, or empty string if not found
    """
    with open(main_nf_path) as f:
        data = f.read()

        if "container" not in data:
            log.debug(f"Could not find a container directive in {main_nf_path}")
            return ""

        # Regex explained:
        #  1. Match "container" followed by whitespace
        #  2. Capturing group 1: Match a quote char " or '
        #  3. Capturing group 2: Match any characters (the container string, including newlines)
        #  4. Match whatever was captured in group 1 (same quote char)
        # DOTALL flag makes . match newlines for multi-line container directives
        regex_container = r'container\s+(["\'])(.+?)\1'
        match = re.search(regex_container, data, re.DOTALL)
        if not match:
            component_info = f" for {component_name}" if component_name else ""
            log.warning(f"Container{component_info} could not be extracted from {main_nf_path} with regex")
            return ""

        # Return the container string (group 2)
        container = match.group(2)
        return container


def repo_full_name_from_remote(remote_url: str) -> str:
    """
    Extracts the path from the remote URL
    See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
    """

    if remote_url.startswith(("https://", "http://", "ftps://", "ftp://", "ssh://")):
        # Parse URL and remove the initial '/'
        path = urlparse(remote_url).path.lstrip("/")
    elif "git@" in remote_url:
        # Extract the part after 'git@' and parse it
        path = urlparse(remote_url.split("git@")[-1]).path
    else:
        path = urlparse(remote_url).path

    # Remove the file extension from the path
    path, _ = os.path.splitext(path)

    return path


def get_installed_modules(directory: Path, repo_type="modules") -> tuple[list[str], list[NFCoreComponent]]:
    """
    Make a list of all modules installed in this repository

    Returns a tuple of two lists, one for local modules
    and one for nf-core modules. The local modules are represented
    as direct filepaths to the module '.nf' file.
    Nf-core module are returned as file paths to the module directories.
    In case the module contains several tools, one path to each tool directory
    is returned.

    returns (local_modules, nfcore_modules)
    """
    # initialize lists
    local_modules: list[str] = []
    nfcore_modules_names: list[str] = []
    local_modules_dir: Path | None = None
    nfcore_modules_dir = Path(directory, "modules", "nf-core")

    # Get local modules
    if repo_type == "pipeline":
        local_modules_dir = Path(directory, "modules", "local")

        # Filter local modules
        if local_modules_dir.exists():
            local_modules = os.listdir(local_modules_dir)
            local_modules = sorted([x for x in local_modules if x.endswith(".nf")])

    # Get nf-core modules
    if nfcore_modules_dir.exists():
        for m in sorted([m for m in nfcore_modules_dir.iterdir() if not m == "lib"]):
            if not m.is_dir():
                raise ModuleExceptionError(
                    f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                )
            m_content = [d.name for d in m.iterdir()]
            # Not a module, but contains sub-modules
            if "main.nf" not in m_content:
                for tool in m_content:
                    if (m / tool).is_dir() and "main.nf" in [d.name for d in (m / tool).iterdir()]:
                        nfcore_modules_names.append(str(Path(m.name, tool)))
            else:
                nfcore_modules_names.append(m.name)

    # Make full (relative) file paths and create NFCoreComponent objects
    if local_modules_dir:
        local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]

    nfcore_modules = [
        NFCoreComponent(
            m,
            "nf-core/modules",
            Path(nfcore_modules_dir, m),
            repo_type=repo_type,
            base_dir=directory,
            component_type="modules",
        )
        for m in nfcore_modules_names
    ]

    return local_modules, nfcore_modules


def load_edam():
    """Load the EDAM ontology from the nf-core repository"""
    edam_formats = {}
    try:
        response = requests.get("https://edamontology.org/EDAM.tsv")
    except requests.exceptions.RequestException as e:
        log.warning(f"Failed to load EDAM ontology: {e}")
        return edam_formats
    for line in response.content.splitlines():
        fields = line.decode("utf-8").split("\t")
        if fields[0].split("/")[-1].startswith("format"):
            # We choose an already provided extension
            if fields[14]:
                extensions = fields[14].split("|")
                for extension in extensions:
                    if extension not in edam_formats:
                        edam_formats[extension] = (fields[0], fields[1])  # URL, name
    return edam_formats


def filter_modules_by_name(modules: list[NFCoreComponent], module_name: str) -> list[NFCoreComponent]:
    """
    Filter modules by name, supporting exact matches and tool family matching.

    Args:
        modules (list[NFCoreComponent]): List of modules to filter
        module_name (str): The module name or prefix to match

    Returns:
        list[NFCoreComponent]: List of matching modules
    """
    # First try to find an exact match
    exact_matches = [m for m in modules if m.component_name == module_name]
    if exact_matches:
        return exact_matches
    # If no exact match, look for modules that start with the given name (subtools)
    return [m for m in modules if m.component_name.startswith(module_name)]


def prompt_module_selection(
    modules: list[NFCoreComponent], component_type: str = "modules", action: str = "Select", allow_all: bool = True
) -> str | None:
    """
    Prompt user to select a specific module or all modules.

    Args:
        modules (list[NFCoreComponent]): List of available modules to choose from
        component_type (str): The component type (default: "modules", can also be "subworkflows")
        action (str): The action verb to use in the prompt message (e.g., "Lint", "Install", "Update", "Bump versions for")
        allow_all (bool): Whether to show "All modules" option (default: True)

    Returns:
        str | None: The selected module name, or None if "All modules" was selected
    """
    import questionary

    from nf_core.utils import nfcore_question_style

    if not modules:
        return None

    component_singular = component_type.rstrip("s")  # "modules" -> "module"

    # If allow_all is False, skip the "all or named" question and go straight to module selection
    if not allow_all:
        question = {
            "type": "autocomplete",
            "name": "tool_name",
            "message": "Tool name:",
            "choices": [m.component_name for m in modules],
        }
        answer = questionary.unsafe_prompt([question], style=nfcore_question_style)
        return answer.get("tool_name")

    # Otherwise, show the "all or named" question
    questions = [
        {
            "type": "list",
            "name": f"all_{component_type}",
            "message": f"{action} all {component_type} or a single named {component_singular}?",
            "choices": [f"All {component_type}", f"Named {component_singular}"],
        },
        {
            "type": "autocomplete",
            "name": "tool_name",
            "message": "Tool name:",
            "when": lambda x: x[f"all_{component_type}"] == f"Named {component_singular}",
            "choices": [m.component_name for m in modules],
        },
    ]
    answers = questionary.unsafe_prompt(questions, style=nfcore_question_style)
    return answers.get("tool_name")
