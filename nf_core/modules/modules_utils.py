import csv
import logging
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, ValidationInfo, field_validator, model_validator

from nf_core.utils import (
    CONTAINER_PLATFORMS,
    CONTAINER_SYSTEMS,
    NFCORE_CACHE_DIR,
    REQUIRED_CONTAINER_PLATFORMS,
)

from ..components.nfcore_component import NFCoreComponent

log = logging.getLogger(__name__)

EDAM_TSV_URL = "https://edamontology.org/EDAM.tsv"
EDAM_CACHE_TTL = 7 * 24 * 60 * 60  # one week


class ModuleExceptionError(Exception):
    """Exception raised when there was an error with module commands"""

    pass


class ContainerEntry(BaseModel):
    name: str
    build_id: str = ""
    scan_id: str = ""
    https: str = ""

    @property
    def build_hash(self) -> str:
        """Hash part of the Wave build ID (``bd-<hash>_<build>``)."""
        parts = self.build_id.removeprefix("bd-").split("_")
        return parts[0] if parts else ""

    @property
    def tag_hash(self) -> str:
        """Hash encoded in the image tag (``name:<version>--<hash>``, or a bare hex tag)."""
        name = self.name
        if "://" in name:
            name = name.split("://", 1)[1]
        if "@" in name:
            name = name.split("@", 1)[0]
        if ":" not in name:
            return ""
        tag = name.rsplit(":", 1)[1]
        if "--" in tag:
            return tag.rsplit("--", 1)[1]
        tag_lower = tag.lower()
        return tag if len(tag_lower) >= 8 and all(c in "0123456789abcdef" for c in tag_lower) else ""


class CondaEntry(BaseModel):
    lock_file: str = ""


class MetaYmlContainers(BaseModel):
    docker: dict[str, ContainerEntry] = {}
    singularity: dict[str, ContainerEntry] = {}
    conda: dict[str, CondaEntry] = {}

    @field_validator("docker", "singularity", "conda", mode="after")
    @classmethod
    def check_keys_against_container_platforms(cls, value: dict) -> dict:
        # Check if all used keys are valid platforms
        for plf_key in value:
            if plf_key not in CONTAINER_PLATFORMS:
                raise ValueError(f"Invalid platform key: {plf_key}")

        return value

    def dump_for_meta_yml(self) -> dict:
        """
        ``model_dump`` shaped for the meta.yml JSON schema: ``name``/``build_id`` are
        always emitted (the schema requires them, empty or not), while the optional
        fields (``https``, ``scan_id``) are omitted when empty — an empty ``https``
        would violate the schema's ``^https://`` pattern.
        """
        dump = self.model_dump()
        for platforms in dump.values():
            for entry in platforms.values():
                for key in ("https", "scan_id"):
                    if not entry.get(key, True):
                        del entry[key]
        return dump

    @model_validator(mode="after")
    def check_container_systems_complete(self, info: ValidationInfo) -> "MetaYmlContainers":
        """
        Require a non-empty section with an entry for every *required* platform
        (``REQUIRED_CONTAINER_PLATFORMS``), for each container system named in
        ``context={"require_complete": [...]}`` (``True`` means all of
        ``CONTAINER_SYSTEMS``, i.e. conda is exempt). Optional platforms such as
        ``linux/arm64`` are validated when present but never required. Plain
        construction (e.g. the partial states built up during container builds) is
        not affected.
        """
        require = (info.context or {}).get("require_complete")
        if not require:
            return self
        for system in CONTAINER_SYSTEMS if require is True else require:
            entries = getattr(self, system)
            if not entries:
                raise ValueError(f"No containers specified for {system}")
            for plf in REQUIRED_CONTAINER_PLATFORMS:
                if plf not in entries:
                    raise ValueError(f"No {system} entries found for expected platform: {plf}")
        return self


def module_uses_dockerfile(module: NFCoreComponent) -> bool:
    """Return True if the module has a Dockerfile (in its dir or parent) but no environment.yml."""
    env_yml = module.environment_yml
    if env_yml is not None and Path(env_yml).exists():
        return False
    component_dir = Path(module.component_dir)
    return (component_dir / "Dockerfile").exists() or (component_dir.parent / "Dockerfile").exists()


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
    return str(Path(path).with_suffix(""))


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
            local_modules = sorted([x.name for x in local_modules_dir.iterdir() if x.suffix == ".nf"])

    # Get nf-core modules
    if nfcore_modules_dir.exists():
        for m in sorted([m for m in nfcore_modules_dir.iterdir() if m != "lib"]):
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
        local_modules = [str(local_modules_dir / m) for m in local_modules]

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


COL_URI, COL_LABEL, COL_SYNONYMS, COL_EXTENSION = 0, 1, 2, 14
_EXTENSION_LIKE = re.compile(r"[a-z0-9._-]{1,12}\Z")
_OBSOLETE_HINTS = ("obsolete", "deprecated")


def _parse_edam(data_bytes):
    """Build {extension -> (uri, label)} from EDAM.tsv.

    Keys come from three places, in decreasing order of authority:
      1. the curated "File extension" column,
      2. the concept's preferred label,
      3. its exact synonyms, when they look like a file extension.
    A token claimed by two different format concepts is dropped as ambiguous.
    """
    rows = list(csv.reader(data_bytes.decode("utf-8").splitlines(), delimiter="\t"))
    formats = [
        r
        for r in rows[1:]
        if r
        and r[COL_URI].split("/")[-1].startswith("format")
        and not any(h in " ".join(r[:3]).lower() for h in _OBSOLETE_HINTS)
    ]

    curated = {}
    for r in formats:
        if len(r) > COL_EXTENSION and r[COL_EXTENSION]:
            for ext in r[COL_EXTENSION].split("|"):
                curated.setdefault(ext, (r[COL_URI], r[COL_LABEL]))

    claims = defaultdict(set)
    for r in formats:
        tokens = set()
        if len(r) > COL_LABEL and r[COL_LABEL].strip():
            tokens.add(r[COL_LABEL].strip().lower())
        if len(r) > COL_SYNONYMS and r[COL_SYNONYMS].strip():
            for syn in r[COL_SYNONYMS].split("|"):
                syn = syn.strip().lower()
                if syn and _EXTENSION_LIKE.match(syn):
                    tokens.add(syn)
        for t in tokens:
            claims[t].add((r[COL_URI], r[COL_LABEL]))

    edam_formats = {t: sorted(v)[0] for t, v in claims.items() if len(v) == 1}
    ambiguous = sorted(t for t, v in claims.items() if len(v) > 1)
    if ambiguous:
        log.debug(f"EDAM tokens claimed by multiple format concepts, skipped: {ambiguous}")
    edam_formats.update(curated)  # the curated column always wins
    return edam_formats


def cache_is_expired(path: Path) -> bool:

    return time.time() - path.stat().st_mtime > EDAM_CACHE_TTL


def load_edam(cache_dir=None):
    """Load the EDAM ontology from the nf-core repository.

    Returns:
        dict: mapping of file extension to ``(URL, name)``. Empty when the
        ontology could not be loaded. Callers that need to tell "failed to
        load" apart from "loaded, no match" should use
        :func:`load_edam_with_status`.
    """
    edam_formats, _ = load_edam_with_status(cache_dir)
    return edam_formats


def load_edam_with_status(cache_dir=None):
    """Load the EDAM ontology, reporting whether the load succeeded.

    Returns:
        (edam_formats, ok): ``ok`` is False when the ontology could not be
        downloaded or read, so callers can skip ontology annotation rather
        than writing empty lists.
    """
    cache_path = Path(cache_dir if cache_dir is not None else NFCORE_CACHE_DIR) / "EDAM.tsv"

    if cache_path.exists() and cache_is_expired(cache_path):
        log.debug("Cached EDAM ontology expired; removing old cache file")
        cache_path.unlink(missing_ok=True)

    if not cache_path.exists():
        log.debug("EDAM.tsv file not found in cache; downloading")
        try:
            response = requests.get(EDAM_TSV_URL, timeout=15)
            response.raise_for_status()
            data_bytes = response.content
            cache_path.write_bytes(data_bytes)
        except requests.exceptions.RequestException as e:
            log.warning(f"Failed to download EDAM ontology: {e}. Ontology annotations will be left unchanged.")
            return {}, False
    else:
        log.debug("Using EDAM.tsv file found in cache")
        try:
            data_bytes = cache_path.read_bytes()
        except OSError as e:
            log.warning(f"Failed to load EDAM ontology: {e}. Ontology annotations will be left unchanged.")
            return {}, False

    return _parse_edam(data_bytes), True


def scan_modules_dir(modules_dir: Path) -> list[str]:
    """
    Scan a modules directory for main.nf files and return module names relative to modules_dir.

    Args:
        modules_dir: Directory to scan

    Returns:
        List of module names relative to modules_dir
    """
    if not modules_dir.exists():
        return []
    return [str(main_nf.parent.relative_to(modules_dir)) for main_nf in modules_dir.rglob("main.nf")]


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
