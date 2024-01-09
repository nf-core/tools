import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from ..components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)


class ModuleExceptionError(Exception):
    """Exception raised when there was an error with module commands"""

    pass


def repo_full_name_from_remote(remote_url: str) -> str:
    """
    Extracts the path from the remote URL
    See https://mirrors.edge.kernel.org/pub/software/scm/git/docs/git-clone.html#URLS for the possible URL patterns
    """
    # Check whether we have a https or ssh url
    if remote_url.startswith("https"):
        path = urlparse(remote_url).path
        # Remove the intial '/'
        path = path[1:]
        # Remove extension
        path = os.path.splitext(path)[0]
    else:
        # Remove the initial `git@``
        split_path: list = remote_url.split("@")
        path = split_path[-1] if len(split_path) > 1 else split_path[0]
        path = urlparse(path).path
        # Remove extension
        path = os.path.splitext(path)[0]
    return path


def get_installed_modules(dir: str, repo_type="modules") -> Tuple[List[str], List[NFCoreComponent]]:
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
    local_modules: List[str] = []
    nfcore_modules_names: List[str] = []
    local_modules_dir: Optional[str] = None
    nfcore_modules_dir = os.path.join(dir, "modules", "nf-core")

    # Get local modules
    if repo_type == "pipeline":
        local_modules_dir = os.path.join(dir, "modules", "local")

        # Filter local modules
        if os.path.exists(local_modules_dir):
            local_modules = os.listdir(local_modules_dir)
            local_modules = sorted([x for x in local_modules if x.endswith(".nf")])

    # Get nf-core modules
    if os.path.exists(nfcore_modules_dir):
        for m in sorted([m for m in os.listdir(nfcore_modules_dir) if not m == "lib"]):
            if not os.path.isdir(os.path.join(nfcore_modules_dir, m)):
                raise ModuleExceptionError(
                    f"File found in '{nfcore_modules_dir}': '{m}'! This directory should only contain module directories."
                )
            m_content = os.listdir(os.path.join(nfcore_modules_dir, m))
            # Not a module, but contains sub-modules
            if "main.nf" not in m_content:
                for tool in m_content:
                    nfcore_modules_names.append(os.path.join(m, tool))
            else:
                nfcore_modules_names.append(m)

    # Make full (relative) file paths and create NFCoreComponent objects
    if local_modules_dir:
        local_modules = [os.path.join(local_modules_dir, m) for m in local_modules]

    nfcore_modules = [
        NFCoreComponent(
            m,
            "nf-core/modules",
            Path(nfcore_modules_dir, m),
            repo_type=repo_type,
            base_dir=Path(dir),
            component_type="modules",
        )
        for m in nfcore_modules_names
    ]

    return local_modules, nfcore_modules
