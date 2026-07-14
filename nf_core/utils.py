"""
Common utility functions for the nf-core python package.
"""

import ast
import datetime
import errno
import fnmatch
import functools
import hashlib
import importlib
import io
import json
import logging
import mimetypes
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager, suppress
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

from packaging.version import InvalidVersion, Version
from rich.live import Live
from rich.spinner import Spinner

import nf_core

if TYPE_CHECKING:
    from nf_core.pipelines.schema import PipelineSchema
    from nf_core.pydantic_models import NFCoreYamlConfig

log = logging.getLogger(__name__)

# ASCII nf-core logo
nfcore_logo = [
    r"[green]                                          ,--.[grey39]/[green],-.",
    r"[blue]          ___     __   __   __   ___     [green]/,-._.--~\ ",
    r"[blue]    |\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {",
    r"[blue]    | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,",
    r"[green]                                          `._,._,'",
]


def lazy_attrs(module_globals: dict, mapping: dict[str, "str | Callable"]):
    """Build module-level ``__getattr__`` and ``__dir__`` for lazy attributes (PEP 562).

    Each attribute maps either to the dotted path of the module to import it
    from, or to a zero-argument callable that builds it. Resolved attributes
    are cached in the module's globals, so the hook only fires once per name.

    Usage::

        __getattr__, __dir__ = lazy_attrs(globals(), {"PipelineCreateApp": "nf_core.pipelines.create"})
    """

    def module_getattr(name):
        target = mapping.get(name)
        if target is None:
            raise AttributeError(f"module {module_globals['__name__']!r} has no attribute {name!r}")
        value = target() if callable(target) else getattr(importlib.import_module(target), name)
        module_globals[name] = value
        return value

    def module_dir():
        return sorted(set(module_globals) | set(mapping))

    return module_getattr, module_dir


# Custom style for questionary (built lazily to keep CLI start-up fast)
@functools.cache
def _nfcore_question_style():
    import prompt_toolkit.styles

    return prompt_toolkit.styles.Style(
        [
            ("qmark", "fg:ansiblue bold"),  # token in front of the question
            ("question", "bold"),  # question text
            (
                "answer",
                "fg:ansigreen nobold bg:",
            ),  # submitted answer text behind the question
            (
                "pointer",
                "fg:ansiyellow bold",
            ),  # pointer used in select and checkbox prompts
            (
                "highlighted",
                "fg:ansiblue bold",
            ),  # pointed-at choice in select and checkbox prompts
            (
                "selected",
                "fg:ansiyellow noreverse bold",
            ),  # style for a selected item of a checkbox
            ("separator", "fg:ansiblack"),  # separator in lists
            ("instruction", ""),  # user instructions for select, rawselect, checkbox
            ("text", ""),  # plain text
            (
                "disabled",
                "fg:gray italic",
            ),  # disabled choices for select and checkbox prompts
            ("choice-default", "fg:ansiblack"),
            ("choice-default-changed", "fg:ansiyellow"),
            ("choice-required", "fg:ansired"),
        ]
    )


# Lazy imports to keep CLI start-up fast
__getattr__, __dir__ = lazy_attrs(
    globals(),
    {
        "nfcore_question_style": _nfcore_question_style,
        "GitHubAPISession": "nf_core.github_api",
        "gh_api": "nf_core.github_api",
        "NFCoreTemplateConfig": "nf_core.pydantic_models",
        "NFCoreYamlLintConfig": "nf_core.pydantic_models",
        "NFCoreYamlConfig": "nf_core.pydantic_models",
    },
)


def is_interactive() -> bool:
    """Check if the current session is interactive (has a TTY on stdin, stdout, and stderr)."""
    return sys.stdin.isatty() and sys.stdout.isatty() and sys.stderr.isatty()


NFCORE_CACHE_DIR = Path(
    os.environ.get("XDG_CACHE_HOME") or Path(os.getenv("HOME") or "") / ".cache",
    "nfcore",
)
NFCORE_DIR = Path(
    os.environ.get("XDG_CONFIG_HOME") or Path(os.getenv("HOME") or "") / ".config",
    "nfcore",
)


CONTAINER_SYSTEMS = ["docker", "singularity"]
CONTAINER_PLATFORMS = ["linux/amd64", "linux/arm64"]
# Platforms a module must provide containers for. Others (e.g. linux/arm64) are
# supported and validated when present, but not required.
REQUIRED_CONTAINER_PLATFORMS = ["linux/amd64"]


class ContainerRegistryUrls(Enum):
    SEQERA_DOCKER = "community.wave.seqera.io/library"
    SEQERA_SINGULARITY = "community-cr-prod.seqera.io/docker/registry/v2"
    GALAXY_SINGULARITY = "depot.galaxyproject.org/singularity"


def unquote(s: str) -> str:
    """
    Remove paired quotes (single or double) from start and end of string.

    Uses ast.literal_eval to safely parse Python string literals, preserving
    the original string if it's not a valid literal.

    Special handling for ruamel.yaml DoubleQuotedScalarString to preserve
    strings that should not be converted to numbers (e.g., "123" stays as string).

    Args:
        s: String potentially containing quotes

    Returns:
        String with outer quotes removed if present, otherwise original string
    """
    import ruamel.yaml.scalarstring

    if isinstance(
        s, (ruamel.yaml.scalarstring.DoubleQuotedScalarString, ruamel.yaml.scalarstring.SingleQuotedScalarString)
    ):
        return s

    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return s


# The version check never fetches on the hot path (update-notifier pattern):
# it only reads the cached remote version, and refreshes the cache in a
# detached background process so that no run ever blocks on the network.
REMOTE_VERSION_CACHE = Path(NFCORE_CACHE_DIR, "latest_version.json")
REMOTE_VERSION_CACHE_EXPIRY = 60 * 60 * 24  # refresh at most once a day
REMOTE_VERSION_REFRESH_BACKOFF = 60 * 10  # wait at least this long between refresh attempts


def _load_version_cache() -> dict:
    try:
        with open(REMOTE_VERSION_CACHE) as fh:
            cached = json.load(fh)
        if isinstance(cached, dict):
            return cached
    except (OSError, ValueError):
        pass
    return {}


def _load_cached_remote_version() -> str | None:
    cached = _load_version_cache()
    try:
        if time.time() - cached["timestamp"] < REMOTE_VERSION_CACHE_EXPIRY:
            Version(cached["version"])  # guard against a corrupted cache
            return cached["version"]
    except (KeyError, TypeError, InvalidVersion):
        pass
    return None


def _spawn_remote_version_refresh(source_url: str) -> None:
    """Kick off a detached background process to refresh the remote version cache."""
    try:
        cached = _load_version_cache()
        if time.time() - float(cached.get("attempted_at") or 0) < REMOTE_VERSION_REFRESH_BACKOFF:
            return
        # Record the attempt up front, so failed refreshes back off instead of respawning every run
        cached["attempted_at"] = time.time()
        setup_nfcore_cachedir()
        with open(REMOTE_VERSION_CACHE, "w") as fh:
            json.dump(cached, fh)
        subprocess.Popen(
            [sys.executable, "-m", "nf_core.version_updater", source_url, str(REMOTE_VERSION_CACHE)],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as e:
        log.debug(f"Could not start background version check: {e}")


def check_if_outdated(
    current_version=None,
    remote_version=None,
    source_url="https://nf-co.re/tools_version",
):
    """
    Check if the current version of nf-core is outdated
    """
    # Exit immediately if disabled via ENV var
    if os.environ.get("NFCORE_NO_VERSION_CHECK", False):
        return (False, "", "")
    # Set and clean up the current version string
    if current_version is None:
        current_version = nf_core.__version__
    current_version = re.sub(r"[^0-9\.]", "", current_version)
    # Build the URL to check against
    source_url = os.environ.get("NFCORE_VERSION_URL", source_url)
    source_url = f"{source_url}?v={current_version}"
    # check if we have a newer version without blocking the rest of the script
    is_outdated = False
    if remote_version is None:  # we set it manually for tests
        remote_version = _load_cached_remote_version()
        if remote_version is None:
            # No fresh cache - refresh it in the background for the next run
            _spawn_remote_version_refresh(source_url)
    if remote_version is not None and Version(remote_version) > Version(current_version):
        is_outdated = True
    return (is_outdated, current_version, remote_version)


def rich_force_colors():
    """
    Check if any environment variables are set to force Rich to use coloured output
    """
    if os.getenv("GITHUB_ACTIONS") or os.getenv("FORCE_COLOR") or os.getenv("PY_COLORS"):
        return True
    return None


class Pipeline:
    """Object to hold information about a local pipeline.

    Args:
        path (str): The path to the nf-core pipeline directory.

    Attributes:
        conda_config (dict): The parsed conda configuration file content (``environment.yml``).
        conda_package_info (dict): The conda package(s) information, based on the API requests to Anaconda cloud.
        nf_config (dict): The Nextflow pipeline configuration file content.
        files (list): A list of files found during the linting process.
        git_sha (str): The git sha for the repo commit / current GitHub pull-request (`$GITHUB_PR_COMMIT`)
        minNextflowVersion (str): The minimum required Nextflow version to run the pipeline.
        wf_path (str): Path to the pipeline directory.
        pipeline_name (str): The pipeline name, without the `nf-core` tag, for example `hlatyping`.
        schema_obj (obj): A :class:`PipelineSchema` object
    """

    def __init__(self, wf_path: Path) -> None:
        """Initialise pipeline object"""
        import git

        self.conda_config: dict = {}
        self.conda_package_info: dict = {}
        self.nf_config: dict = {}
        self.files: list[Path] = []
        self.git_sha: str | None = None
        self.minNextflowVersion: str | None = None
        self.wf_path = Path(wf_path).resolve()
        self.pipeline_name: str | None = None
        self.pipeline_prefix: str | None = None
        self.schema_obj: PipelineSchema | None = None
        self.repo: git.Repo | None = None

        try:
            self.repo = git.Repo(self.wf_path)
            self.git_sha = self.repo.head.object.hexsha
        except git.exc.GitError as e:
            log.debug(f"Could not find git hash for pipeline: {self.wf_path}. {e}")

        # Overwrite if we have the last commit from the PR - otherwise we get a merge commit hash
        if os.environ.get("GITHUB_PR_COMMIT", "") != "":
            self.git_sha = os.environ["GITHUB_PR_COMMIT"]

    def __repr__(self) -> str:
        return f"<Pipeline '{self.pipeline_name}' at {self.wf_path}>"

    def _load(self) -> bool:
        """Run core load functions"""

        return self.load_pipeline_config() and self._load_conda_environment()

    def _load_conda_environment(self) -> bool:
        """Try to load the pipeline environment.yml file, if it exists"""
        import yaml

        try:
            with open(Path(self.wf_path, "environment.yml")) as fh:
                self.conda_config = yaml.safe_load(fh)
            return True
        except FileNotFoundError:
            log.debug("No conda `environment.yml` file found.")
            return False

    def _fp(self, fn: str | Path) -> Path:
        """Convenience function to get full path to a file in the pipeline"""
        return Path(self.wf_path, fn)

    def list_files(self) -> list[Path]:
        """Get a list of all files in the pipeline"""
        files = []
        try:
            # First, try to get the list of files using git
            git_ls_files = subprocess.check_output(["git", "ls-files"], cwd=self.wf_path).splitlines()
            for fn in git_ls_files:
                full_fn = Path(self.wf_path) / fn.decode("utf-8")
                if full_fn.is_file():
                    files.append(full_fn)
                else:
                    log.debug(f"`git ls-files` returned '{full_fn}' but could not open it!")
        except subprocess.CalledProcessError:
            # Failed, so probably not initialised as a git repository - just a list of all files
            files = []
            for file_path in self.wf_path.rglob("*"):
                if file_path.is_file():
                    # Append the file path to the list
                    files.append(file_path)
            if len(files) == 0:
                log.debug(f"No files found in pipeline: {self.wf_path}")

        return files

    def load_pipeline_config(self) -> bool:
        """Get the nextflow config for this pipeline

        Once loaded, set a few convenience reference class attributes
        """
        self.nf_config = fetch_wf_config(self.wf_path)
        manifest = self.nf_config.get("manifest", {})

        self.pipeline_prefix, self.pipeline_name = manifest.get("name", "/").split("/")

        nextflow_version_match = re.search(r"(?P<version>[0-9\.]+(-edge)?)", manifest.get("nextflowVersion", "") or "")
        if nextflow_version_match:
            self.minNextflowVersion = nextflow_version_match.group("version")
            return True
        return False


def is_pipeline_directory(wf_path):
    """
    Checks if the specified directory have the minimum required files
    ('main.nf', 'nextflow.config') for a pipeline directory

    Args:
        wf_path (str): The directory to be inspected

    Raises:
        UserWarning: If one of the files are missing
    """
    for fn in ["main.nf", "nextflow.config"]:
        if not Path(wf_path, fn).is_file():
            if wf_path == ".":
                warning = f"Current directory is not a pipeline - '{fn}' is missing."
            else:
                warning = f"'{wf_path}' is not a pipeline - '{fn}' is missing."
            raise UserWarning(warning)


# This is the minimal version of Nextflow required to fetch containers with `nextflow inspect`
NF_INSPECT_MIN_NF_VERSION = (25, 4, 4, False)

# This is the maximal version of nf-core/tools that does not require `nextflow inspect` for downloads
NFCORE_VER_LAST_WITHOUT_NF_INSPECT = (3, 3, 2)


# Pretty print a Nextflow version tuple
def pretty_nf_version(version: tuple[int, int, int, bool]) -> str:
    return f"{version[0]}.{version[1]:02}.{version[2]}" + ("-edge" if version[3] else "")


@lru_cache(maxsize=1)
def get_nf_version() -> tuple[int, int, int, bool] | None:
    """Get the version of Nextflow installed on the system. Cached for the lifetime of the process."""
    try:
        cmd_out = run_cmd("nextflow", "-v")
        if cmd_out is None:
            raise RuntimeError("Failed to run Nextflow version check.")
        out, _ = cmd_out
        out_str = str(out, encoding="utf-8")  # Ensure we have a string

        version_str = out_str.strip().split()[-1]

        # Check if we are using an edge release
        is_edge = False
        edge_split = version_str.split("-")
        if len(edge_split) > 1:
            is_edge = True
            version_str = edge_split[0]

        split_version_str = version_str.split(".")
        parsed_version_tuple = (
            int(split_version_str[0]),
            int(split_version_str[1]),
            int(split_version_str[2]),
            is_edge,
        )
        return parsed_version_tuple
    except (subprocess.CalledProcessError, IndexError, ValueError) as e:
        log.warning(f"Error getting Nextflow version: {e}")
        return None


# Check that the Nextflow version >= the minimal version required
# This is used to ensure that we can run `nextflow inspect`
def check_nextflow_version(minimal_nf_version: tuple[int, int, int, bool], silent=False) -> bool:
    """Check the version of Nextflow installed on the system.

    Args:
        minimal_nf_version (tuple[int, int, int, bool]): The minimal version of Nextflow required.
        silent (bool): Whether to log the version or not.
    Returns:
        bool: True if the installed version is greater than or equal to `minimal_nf_version`
    """
    nf_version = get_nf_version()
    if nf_version is None:
        return False

    parsed_version_str = pretty_nf_version(nf_version)

    if silent:
        log.debug(f"Detected Nextflow version {parsed_version_str}")
    else:
        log.info(f"Detected Nextflow version {parsed_version_str}")

    return nf_version >= minimal_nf_version


def read_module_name(main_nf: Path) -> str | None:
    """Return the process name declared in a Nextflow ``main.nf`` file, or ``None``."""
    nf_process_name_regex = re.compile(r"^\s*process\s+(\w+)\s*\{", re.MULTILINE)
    try:
        match = nf_process_name_regex.search(main_nf.read_text())
    except OSError:
        return None
    return match.group(1) if match else None


def fetch_wf_config(wf_path: Path, cache_config: bool = True) -> dict:
    """Uses Nextflow to retrieve the the configuration variables
    from a Nextflow workflow.

    Args:
        wf_path (str): Nextflow workflow file system path.
        cache_config (bool): cache configuration or not (def. True)

    Returns:
        dict: Workflow configuration settings.
    """

    log.debug(f"Got '{wf_path}' as path")
    wf_path = Path(wf_path)
    config: dict[str, Any] = {}
    cache_fn = None
    cache_basedir = None
    cache_path = None

    # Nextflow home directory - use env var if set, or default to ~/.nextflow
    nxf_home = Path(os.environ.get("NXF_HOME", Path(os.getenv("HOME") or "", ".nextflow")))

    # Build a cache directory if we can
    if nxf_home.is_dir():
        cache_basedir = Path(nxf_home, "nf-core")
        if not cache_basedir.is_dir():
            cache_basedir.mkdir(parents=True, exist_ok=True)

    # If we're given a workflow object with a commit, see if we have a cached copy
    cache_fn = None
    # Make a filename based on file contents
    concat_hash = ""
    for fn in ["nextflow.config", "main.nf"]:
        try:
            with open(wf_path / fn, "rb") as fh:
                concat_hash += hashlib.sha256(fh.read()).hexdigest()
        except FileNotFoundError:
            pass
    # Hash the hash
    if len(concat_hash) > 0:
        bighash = hashlib.sha256(concat_hash.encode("utf-8")).hexdigest()
        cache_fn = f"wf-config-cache-{bighash[:25]}.json"

    if cache_basedir and cache_fn:
        cache_path = Path(cache_basedir, cache_fn)
        if cache_path.is_file() and cache_config is True:
            log.debug(f"Found a config cache, loading: {cache_path}")
            try:
                with open(cache_path) as fh:
                    config = json.load(fh)
                return config
            except json.JSONDecodeError as e:
                # Log warning but don't raise - just regenerate the cache
                log.warning(f"Unable to load cached JSON file '{cache_path}' due to error: {e}")
                log.debug("Removing corrupted cache file and regenerating...")
                cache_path.unlink(missing_ok=True)
    log.debug("No config cache found")

    # Call `nextflow config`
    result = run_cmd("nextflow", f"config -o json {wf_path}")
    if result is not None:
        nfconfig_raw, _ = result
        try:
            raw_str = nfconfig_raw.decode("utf-8")
            json_start = raw_str.find("{")
            parsed = json.loads(raw_str[json_start:] if json_start >= 0 else raw_str)
            config.update(parsed)
            for k in parsed:
                log.debug(f"Config section: {k}")
        except json.JSONDecodeError as e:
            log.warning(f"Unable to parse nextflow config output as JSON: {e}")

    # Scrape main.nf for additional parameter declarations
    # Values in this file are likely to be complex, so don't both trying to capture them. Just get the param name.

    main_nf = Path(wf_path, "main.nf")
    try:
        with open(main_nf, "rb") as fh:
            params_section = config.setdefault("params", {})
            for line in fh:
                line_str = line.decode("utf-8")
                match = re.match(r"^\s*params\.([a-zA-Z0-9_]+)\s*=(?!=)", line_str)
                if match:
                    params_section[match.group(1)] = None

    except FileNotFoundError as e:
        log.debug(f"Could not open {main_nf} to look for parameter declarations - {e}")

    # If we can, save a cached copy
    # HINT: during testing phase (in test_download, for example) we don't want
    # to save configuration copy in $HOME, otherwise the tests/pipelines/test_download.py::DownloadTest::test_wf_use_local_configs
    # will fail after the first attempt. It's better to not save temporary data
    # in others folders than tmp when doing tests in general
    if cache_path and cache_config:
        log.debug(f"Saving config cache: {cache_path}")
        with open(cache_path, "w") as fh:
            json.dump(config, fh, indent=4)

    return config


def run_cmd(executable: str, cmd: str) -> tuple[bytes, bytes] | None:
    """Run a specified command and capture the output. Handle errors nicely."""
    full_cmd = f"{executable} {cmd}"
    log.debug(f"Running command: {full_cmd}")
    try:
        proc = subprocess.run(shlex.split(full_cmd), capture_output=True, check=False)
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise RuntimeError(
                f"It looks like {executable} is not installed. Please ensure it is available in your PATH."
            ) from e
        return None

    if proc.returncode != 0:
        if executable == "nf-test":
            return (proc.stdout, proc.stderr)
        output = (
            proc.stderr.decode("utf-8", errors="replace").strip()
            if proc.stderr
            else proc.stdout.decode("utf-8", errors="replace").strip()
            if proc.stdout
            else ""
        )
        raise RuntimeError(f"Command '{full_cmd}' failed with exit code {proc.returncode}\n{output}")

    return (proc.stdout, proc.stderr)


def setup_requests_cachedir() -> dict[str, Path | datetime.timedelta | str]:
    """Sets up local caching for faster remote HTTP requests.

    Caching directory will be set up in the user's home directory under
    a .config/nf-core/cache_* subdir.

    Uses requests_cache monkey patching.
    Also returns the config dict so that we can use the same setup with a Session.
    """
    pyversion: str = ".".join(str(v) for v in sys.version_info[0:3])
    cachedir: Path = setup_nfcore_cachedir(f"cache_{pyversion}")
    config: dict[str, Path | datetime.timedelta | str] = {
        "cache_name": Path(cachedir, "github_info"),
        "expire_after": datetime.timedelta(hours=1),
        "backend": "sqlite",
    }

    logging.getLogger("requests_cache").setLevel(logging.WARNING)
    return config


def setup_nfcore_cachedir(cache_fn: str | Path | None = None) -> Path:
    """Sets up local caching for caching files between sessions.

    Creates and returns a subdirectory of the nf-core cache directory,
    or the cache directory itself if no subdirectory is given.
    """
    cachedir = Path(NFCORE_CACHE_DIR, cache_fn) if cache_fn else NFCORE_CACHE_DIR

    try:
        cachedir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        log.warning(f"Could not create cache directory: {cachedir}")

    return cachedir


def wait_cli_function(poll_func: Callable[[], bool], refresh_per_second: int = 20) -> None:
    """
    Display a command-line spinner while calling a function repeatedly.

    Keep waiting until that function returns True

    Arguments:
       poll_func (function): Function to call
       refresh_per_second (int): Refresh this many times per second. Default: 20.

    Returns:
       None. Just sits in an infinite loop until the function returns True.
    """
    try:
        spinner = Spinner("dots2", "Use ctrl+c to stop waiting and force exit.")
        with Live(spinner, refresh_per_second=refresh_per_second):
            while True:
                if poll_func():
                    break
                time.sleep(2)
    except KeyboardInterrupt as e:
        raise AssertionError("Cancelled!") from e


def poll_nfcore_web_api(api_url: str, post_data: dict | None = None) -> dict:
    """
    Poll the nf-core website API

    Takes argument api_url for URL

    Expects API response to be valid JSON and contain a top-level 'status' key.
    """
    import requests
    import requests_cache

    # Run without requests_cache so that we get the updated statuses
    with requests_cache.disabled():
        try:
            if post_data is None:
                response = requests.get(api_url, headers={"Cache-Control": "no-cache"})
            else:
                log.debug(f"requesting {api_url} with {post_data}")
                response = requests.post(url=api_url, data=post_data)
        except requests.exceptions.Timeout as e:
            raise AssertionError(f"URL timed out: {api_url}") from e
        except requests.exceptions.ConnectionError as e:
            raise AssertionError(f"Could not connect to URL: {api_url}") from e
        else:
            if response.status_code != 200 and response.status_code != 301:
                response_content = response.content
                if isinstance(response_content, bytes):
                    response_content = response_content.decode()
                log.debug(f"Response content:\n{response_content}")
                raise AssertionError(
                    f"Could not access remote API results: {api_url} (HTML {response.status_code} Error)"
                )
            # follow redirects
            if response.status_code == 301:
                return poll_nfcore_web_api(response.headers["Location"], post_data)
            try:
                web_response = json.loads(response.content)
                if "status" not in web_response:
                    raise AssertionError
            except (json.decoder.JSONDecodeError, AssertionError, TypeError) as e:
                response_content = response.content
                if isinstance(response_content, bytes):
                    response_content = response_content.decode()
                log.debug(f"Response content:\n{response_content}")
                raise AssertionError(
                    f"nf-core website API results response not recognised: {api_url}\n "
                    "See verbose log for full response"
                ) from e
            else:
                return web_response


def anaconda_package(dep, dep_channels=None):
    """Query conda package information.

    Sends a HTTP GET request to the Anaconda remote API.

    Args:
        dep (str): A conda package name.
        dep_channels (list): list of conda channels to use

    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """
    import requests

    if dep_channels is None:
        dep_channels = ["conda-forge", "bioconda"]

    # Check if each dependency is the latest available version
    if "=" in dep:
        depname, _ = dep.split("=", 1)
    else:
        depname = dep

    # 'defaults' isn't actually a channel name. See https://docs.anaconda.com/anaconda/user-guide/tasks/using-repositories/
    if "defaults" in dep_channels:
        dep_channels.remove("defaults")
        dep_channels.extend(["main", "anaconda", "r", "free", "archive", "anaconda-extras"])
    if "::" in depname:
        dep_channels = [depname.split("::")[0]]
        depname = depname.split("::")[1]

    for ch in dep_channels:
        anaconda_api_url = f"https://api.anaconda.org/package/{ch}/{depname}"
        try:
            response = requests.get(anaconda_api_url, timeout=10)
        except requests.exceptions.Timeout as e:
            raise LookupError(f"Anaconda API timed out: {anaconda_api_url}") from e
        except requests.exceptions.ConnectionError as e:
            raise LookupError("Could not connect to Anaconda API") from e
        else:
            if response.status_code == 200:
                return response.json()
            if response.status_code != 404:
                raise LookupError(
                    f"Anaconda API returned unexpected response code `{response.status_code}` for: "
                    f"{anaconda_api_url}\n{response}"
                )
            # response.status_code == 404
            log.debug(f"Could not find `{dep}` in conda channel `{ch}`")

    # We have looped through each channel and had a 404 response code on everything
    raise ValueError(f"Could not find Conda dependency using the Anaconda API: '{dep}'")


def parse_anaconda_licence(anaconda_response, version=None):
    """Given a response from the anaconda API using anaconda_package, parse the software licences.

    Returns: Set of licence types
    """
    licences = set()
    # Licence for each version
    for f in anaconda_response["files"]:
        if not version or version == f.get("version"):
            with suppress(KeyError):
                licences.add(f["attrs"]["license"])
    # Main licence field
    if len(list(licences)) == 0 and isinstance(anaconda_response["license"], str):
        licences.add(anaconda_response["license"])

    # Clean up / standardise licence names
    clean_licences = []
    for lic in licences:
        lic = re.sub(r"GNU General Public License v\d \(([^\)]+)\)", r"\1", lic)
        lic = re.sub(r"GNU GENERAL PUBLIC LICENSE", "GPL", lic, flags=re.IGNORECASE)
        lic = lic.replace("GPL-", "GPLv")
        lic = re.sub(r"GPL\s*([\d\.]+)", r"GPL v\1", lic)  # Add v prefix to GPL version if none found
        lic = re.sub(r"GPL\s*v(\d).0", r"GPL v\1", lic)  # Remove superfluous .0 from GPL version
        lic = re.sub(r"GPL \(([^\)]+)\)", r"GPL \1", lic)
        lic = re.sub(r"GPL\s*v", "GPL v", lic)  # Normalise whitespace to one space between GPL and v
        lic = re.sub(r"\s*(>=?)\s*(\d)", r" \1\2", lic)  # Normalise whitespace around >= GPL versions
        lic = lic.replace("Clause", "clause")  # BSD capitalisation
        lic = re.sub(r"-only$", "", lic)  # Remove superfluous GPL "only" version suffixes
        clean_licences.append(lic)
    return clean_licences


def pip_package(dep):
    """Query PyPI package information.

    Sends a HTTP GET request to the PyPI remote API.

    Args:
        dep (str): A PyPI package name.

    Raises:
        A LookupError, if the connection fails or times out
        A ValueError, if the package name can not be found
    """
    import requests

    pip_depname, _ = dep.split("=", 1)
    pip_api_url = f"https://pypi.python.org/pypi/{pip_depname}/json"
    try:
        response = requests.get(pip_api_url, timeout=10)
    except requests.exceptions.Timeout as e:
        raise LookupError(f"PyPI API timed out: {pip_api_url}") from e
    except requests.exceptions.ConnectionError as e:
        raise LookupError(f"PyPI API Connection error: {pip_api_url}") from e
    else:
        if response.status_code == 200:
            return response.json()
        raise ValueError(f"Could not find pip dependency using the PyPI API: `{dep}`")


def get_biocontainer_tag(package, version):
    """
    Given a bioconda package and version, looks for Docker and Singularity containers
    using the biocontaineres API, e.g.:
    https://api.biocontainers.pro/ga4gh/trs/v2/tools/{tool}/versions/{tool}-{version}
    Returns the most recent container versions by default.
    Args:
        package (str): A bioconda package name.
        version (str): Version of the bioconda package
    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """

    import requests

    biocontainers_api_url = f"https://api.biocontainers.pro/ga4gh/trs/v2/tools/{package}/versions/{package}-{version}"

    def get_tag_date(tag_date):
        """
        Format a date given by the biocontainers API
        Given format: '2021-03-25T08:53:00Z'
        """
        return datetime.datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ")

    try:
        response = requests.get(biocontainers_api_url)
    except requests.exceptions.ConnectionError as e:
        raise LookupError("Could not connect to biocontainers.pro API") from e
    else:
        if response.status_code == 200:
            try:
                images = response.json()["images"]
                singularity_image = None
                docker_image = None
                all_docker = {}
                all_singularity = {}
                for img in images:
                    # Get all Docker and Singularity images
                    if img["image_type"] == "Docker":
                        # Obtain version and build
                        match = re.search(r"(?::)+([A-Za-z\d\-_.]+)", img["image_name"])
                        if match is not None:
                            all_docker[match.group(1)] = {
                                "date": get_tag_date(img["updated"]),
                                "image": img,
                            }
                    elif img["image_type"] == "Singularity":
                        # Obtain version and build
                        match = re.search(r"(?::)+([A-Za-z\d\-_.]+)", img["image_name"])
                        if match is not None:
                            all_singularity[match.group(1)] = {
                                "date": get_tag_date(img["updated"]),
                                "image": img,
                            }
                # Obtain common builds from Docker and Singularity images
                common_keys = list(all_docker.keys() & all_singularity.keys())
                current_date = None
                docker_image_name = docker_image["image_name"].lstrip("quay.io/") if docker_image is not None else None
                for k in common_keys:
                    # Get the most recent common image
                    date = max(all_docker[k]["date"], all_docker[k]["date"])
                    if docker_image is None or current_date < date:
                        docker_image = all_docker[k]["image"]
                        singularity_image = all_singularity[k]["image"]
                        current_date = date
                        docker_image_name = docker_image["image_name"].lstrip("quay.io/")
                if singularity_image is None:
                    raise LookupError(f"Could not find singularity container for {package}")
                return docker_image_name, singularity_image["image_name"]
            except TypeError as e:
                raise LookupError(f"Could not find docker or singularity container for {package}") from e
        elif response.status_code != 404:
            raise LookupError(f"Unexpected response code `{response.status_code}` for {biocontainers_api_url}")
        elif response.status_code == 404:
            raise ValueError(f"Could not find `{package}` on api.biocontainers.pro")


def custom_yaml_dumper():
    """Overwrite default PyYAML output to make Prettier YAML linting happy"""
    import yaml

    class CustomDumper(yaml.Dumper):
        def represent_dict_preserve_order(self, data):
            """Add custom dumper class to prevent overwriting the global state
            This prevents yaml from changing the output order

            See https://stackoverflow.com/a/52621703/1497385
            """
            return self.represent_dict(data.items())

        def increase_indent(self, flow=False, indentless=False):
            """Indent YAML lists so that YAML validates with Prettier

            See https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586
            """
            return super().increase_indent(flow=flow, indentless=False)

        # HACK: insert blank lines between top-level objects
        # inspired by https://stackoverflow.com/a/44284819/3786245
        # and https://github.com/yaml/pyyaml/issues/127
        def write_line_break(self, data=None):
            super().write_line_break(data)

            if len(self.indents) == 1:
                super().write_line_break()

    CustomDumper.add_representer(dict, CustomDumper.represent_dict_preserve_order)
    return CustomDumper


def is_file_binary(path):
    """Check file path to see if it is a binary file"""
    binary_ftypes = ["image", "application/java-archive", "application/x-java-archive"]
    binary_extensions = [".jpeg", ".jpg", ".png", ".zip", ".gz", ".jar", ".tar"]

    # Check common file extensions
    file_extension = Path(path).suffix
    if file_extension in binary_extensions:
        return True

    # Try to detect binary files
    (ftype, encoding) = mimetypes.guess_type(path, strict=False)
    if encoding is not None or (ftype is not None and any(ftype.startswith(ft) for ft in binary_ftypes)):
        return True


def prompt_remote_pipeline_name(wfs):
    """Prompt for the pipeline name with questionary

    Args:
        wfs: A nf_core.pipelines.list.Workflows() object, where get_remote_workflows() has been called.

    Returns:
        pipeline (str): GitHub repo - username/repo

    Raises:
        AssertionError, if pipeline cannot be found
    """
    import questionary
    import requests

    from nf_core.github_api import gh_api

    if not is_interactive():
        raise UserWarning("No pipeline name provided and session is not interactive (no TTY detected).")
    pipeline = questionary.autocomplete(
        "Pipeline name:",
        choices=[wf.name for wf in wfs.remote_workflows],
        style=_nfcore_question_style(),
    ).unsafe_ask()

    # Check nf-core repos
    for wf in wfs.remote_workflows:
        if wf.full_name == pipeline or wf.name == pipeline:
            return wf.full_name

    # Non nf-core repo on GitHub
    if pipeline.count("/") == 1:
        try:
            gh_api.safe_get(f"https://api.github.com/repos/{pipeline}")
        except requests.exceptions.RequestException:
            # No repo found - pass and raise error at the end
            pass
        else:
            return pipeline

    log.info("Available nf-core pipelines: '{}'".format("', '".join([w.name for w in wfs.remote_workflows])))
    raise AssertionError(f"Not able to find pipeline '{pipeline}'")


def prompt_pipeline_release_branch(
    wf_releases: list[dict[str, Any]], wf_branches: dict[str, Any], multiple: bool = False
) -> tuple[Any, list[str]]:
    """Prompt for pipeline release / branch

    Args:
        wf_releases (array): Array of repo releases as returned by the GitHub API
        wf_branches (array): Array of repo branches, as returned by the GitHub API
        multiple (bool): Allow selection of multiple releases & branches (for Seqera Platform)

    Returns:
        choice (questionary.Choice or bool): Selected release / branch or False if no releases / branches available
    """
    import questionary

    # Prompt user for release tag, tag_set will contain all available.
    choices: list[questionary.Choice] = []
    tag_set: list[str] = []

    # Releases
    if len(wf_releases) > 0:
        for tag in (release.get("tag_name") for release in wf_releases):
            tag_display = [
                ("fg:ansiblue", f"{tag}  "),
                ("class:choice-default", "[release]"),
            ]
            choices.append(questionary.Choice(title=tag_display, value=tag))
            tag_set.append(str(tag))

    # Branches
    for branch in wf_branches:
        branch_display = [
            ("fg:ansiyellow", f"{branch}  "),
            ("class:choice-default", "[branch]"),
        ]
        choices.append(questionary.Choice(title=branch_display, value=branch))
        tag_set.append(branch)

    if len(choices) == 0:
        return [], []

    if not is_interactive():
        raise UserWarning("No release/branch specified and session is not interactive (no TTY detected).")

    if multiple:
        return (
            questionary.checkbox(
                "Select release / branch:", choices=choices, style=_nfcore_question_style()
            ).unsafe_ask(),
            tag_set,
        )

    else:
        return (
            questionary.select(
                "Select release / branch:", choices=choices, style=_nfcore_question_style()
            ).unsafe_ask(),
            tag_set,
        )


def get_repo_releases_branches(pipeline, wfs):
    """Fetches details of a nf-core workflow to download.

    Args:
        pipeline (str): GitHub repo username/repo
        wfs: A nf_core.pipelines.list.Workflows() object, where get_remote_workflows() has been called.

    Returns:
        wf_releases, wf_branches (tuple): Array of releases, Array of branches

    Raises:
        LockupError, if the pipeline can not be found.
    """
    from nf_core.github_api import gh_api

    wf_releases = []
    wf_branches = {}

    # Repo is a nf-core pipeline
    for wf in wfs.remote_workflows:
        if wf.full_name == pipeline or wf.name == pipeline:
            # Set to full name just in case it didn't have the nf-core/ prefix
            pipeline = wf.full_name

            # Store releases and stop loop
            wf_releases = sorted(
                wf.releases,
                key=lambda k: k.get("published_at_timestamp", 0),
                reverse=True,
            )
            break

    # Arbitrary GitHub repo
    else:
        if pipeline.count("/") == 1:
            # Looks like a GitHub address - try working with this repo
            log.debug(
                f"Pipeline '{pipeline}' not in nf-core, but looks like a GitHub address - fetching releases from API"
            )

            # Get releases from GitHub API
            rel_r = gh_api.safe_get(f"https://api.github.com/repos/{pipeline}/releases")

            # Check that this repo existed
            try:
                if rel_r.json().get("message") == "Not Found":
                    raise AssertionError(f"Not able to find pipeline '{pipeline}'")
            except AttributeError:
                # Success! We have a list, which doesn't work with .get() which is looking for a dict key
                wf_releases = sorted(
                    rel_r.json(),
                    key=lambda k: k.get("published_at_timestamp", 0),
                    reverse=True,
                )

                # Get release tag commit hashes
                if len(wf_releases) > 0:
                    # Get commit hash information for each release
                    tags_r = gh_api.safe_get(f"https://api.github.com/repos/{pipeline}/tags")
                    for tag in tags_r.json():
                        for release in wf_releases:
                            if tag["name"] == release["tag_name"]:
                                release["tag_sha"] = tag["commit"]["sha"]

        else:
            log.info("Available nf-core pipelines: '{}'".format("', '".join([w.name for w in wfs.remote_workflows])))
            raise AssertionError(f"Not able to find pipeline '{pipeline}'")

    # Get branch information from github api - should be no need to check if the repo exists again
    branch_response = gh_api.safe_get(f"https://api.github.com/repos/{pipeline}/branches?per_page=100")
    for branch in branch_response.json():
        if (
            branch["name"] != "TEMPLATE"
            and branch["name"] != "initial_commit"
            and not branch["name"].startswith("nf-core-template-merge")
        ):
            wf_branches[branch["name"]] = branch["commit"]["sha"]

    # Return pipeline again in case we added the nf-core/ prefix
    return pipeline, wf_releases, wf_branches


def get_repo_commit(pipeline, commit_id):
    """Check if the repo contains the requested commit_id, and expand it to long form if necessary.

    Args:
        pipeline (str): GitHub repo username/repo
        commit_id: The requested commit ID (SHA). It can be in standard long/short form, or any length.

    Returns:
        commit_id: String or None
    """
    from nf_core.github_api import gh_api

    commit_response = gh_api.get(
        f"https://api.github.com/repos/{pipeline}/commits/{commit_id}", headers={"Accept": "application/vnd.github.sha"}
    )
    if commit_response.status_code == 200:
        return commit_response.text
    else:
        return None


CONFIG_PATHS = [".nf-core.yml", ".nf-core.yaml"]
DEPRECATED_CONFIG_PATHS = [".nf-core-lint.yml", ".nf-core-lint.yaml"]


def load_tools_config(directory: str | Path = ".") -> "tuple[Path | None, NFCoreYamlConfig | None]":
    """
    Parse the nf-core.yml configuration file

    Look for a file called either `.nf-core.yml` or `.nf-core.yaml`

    Also looks for the deprecated file `.nf-core-lint.yml/yaml` and issues
    a warning that this file will be deprecated in the future

    Returns the loaded config dict or False, if the file couldn't be loaded
    """
    import yaml
    from pydantic import ValidationError

    from nf_core.pydantic_models import NFCoreTemplateConfig, NFCoreYamlConfig

    tools_config = {}

    config_fn = get_first_available_path(directory, CONFIG_PATHS)
    if config_fn is None:
        depr_path = get_first_available_path(directory, DEPRECATED_CONFIG_PATHS)
        if depr_path:
            raise UserWarning(
                f"Deprecated `{depr_path.name}` file found! Please rename the file to `{CONFIG_PATHS[0]}`."
            )
        else:
            log.debug(f"Could not find a config file in the directory '{directory}'")
            return Path(directory, CONFIG_PATHS[0]), None
    if not Path(config_fn).is_file():
        raise FileNotFoundError(f"No `.nf-core.yml` file found in the directory '{directory}'")
    with open(config_fn) as fh:
        tools_config = yaml.safe_load(fh)

    # If the file is empty
    if tools_config is None:
        raise AssertionError(f"Config file '{config_fn}' is empty")
    # Check for required fields
    try:
        nf_core_yaml_config = NFCoreYamlConfig(**tools_config)
    except ValidationError as e:
        error_message = f"Config file '{config_fn}' is invalid"
        for error in e.errors():
            error_message += (
                f"\n{'.'.join(str(loc) for loc in error['loc'])}: {error['msg']}\nGot instead: {error['input']}"
            )
        raise AssertionError(error_message) from e

    wf_config = fetch_wf_config(Path(directory))
    if nf_core_yaml_config["repository_type"] == "pipeline" and wf_config:
        # Retrieve information if template from config file is empty
        template = tools_config.get("template")
        config_template_keys = template.keys() if template is not None else []
        # Get author names from contributors first, then fallback to author
        manifest = wf_config.get("manifest", {})
        contributors = manifest.get("contributors", [])
        if contributors:
            names = [c.get("name", "") for c in contributors if c.get("name")]
            author_names = ", ".join(names)
        elif manifest.get("author"):
            author_names = manifest.get("author", "")
        else:
            author_names = None
        if nf_core_yaml_config.template is None:
            # The .nf-core.yml file did not contain template information
            nf_core_yaml_config.template = NFCoreTemplateConfig(
                org="nf-core",
                name=manifest.get("name", "/").split("/")[-1],
                description=manifest.get("description", ""),
                author=author_names,
                version=manifest.get("version", ""),
                outdir=str(directory),
                is_nfcore=True,
            )
        elif "prefix" in config_template_keys or "skip" in config_template_keys:
            # The .nf-core.yml file contained the old prefix or skip keys
            nf_core_yaml_config.template = NFCoreTemplateConfig(
                org=tools_config["template"].get("prefix", tools_config["template"].get("org", "nf-core")),
                name=tools_config["template"].get("name", manifest.get("name", "/").split("/")[-1]),
                description=tools_config["template"].get("description", manifest.get("description", "")),
                author=tools_config["template"].get("author", author_names),
                version=tools_config["template"].get("version", manifest.get("version", "")),
                outdir=tools_config["template"].get("outdir", str(directory)),
                skip_features=tools_config["template"].get("skip", tools_config["template"].get("skip_features")),
                is_nfcore=tools_config["template"].get("prefix", tools_config["template"].get("org")) == "nf-core",
            )

    log.debug("Using config file: %s", config_fn)
    return config_fn, nf_core_yaml_config


def determine_base_dir(directory: Path | str = ".") -> Path:
    base_dir = start_dir = Path(directory).absolute()
    # Only iterate up the tree if the start dir doesn't have a config
    while not get_first_available_path(base_dir, CONFIG_PATHS) and base_dir != base_dir.parent:
        base_dir = base_dir.parent
        config_fn = get_first_available_path(base_dir, CONFIG_PATHS)
        if config_fn:
            break
    return Path(directory) if (base_dir == start_dir or str(base_dir) == base_dir.root) else base_dir


def get_first_available_path(directory: Path | str, paths: list[str]) -> Path | None:
    for p in paths:
        if Path(directory, p).is_file():
            return Path(directory, p)
    return None


def sort_dictionary(d: dict) -> dict:
    """Sorts a nested dictionary recursively"""
    result = {}
    for k, v in sorted(d.items()):
        if isinstance(v, dict):
            result[k] = sort_dictionary(v)
        else:
            result[k] = v
    return result


def plural_s(list_or_int):
    """Return an s if the input is not one or has not the length of one."""
    length = list_or_int if isinstance(list_or_int, int) else len(list_or_int)
    return "s" * (length != 1)


def plural_y(list_or_int):
    """Return 'ies' if the input is not one or has not the length of one, else 'y'."""
    length = list_or_int if isinstance(list_or_int, int) else len(list_or_int)
    return "ies" if length != 1 else "y"


def plural_es(list_or_int):
    """Return a 'es' if the input is not one or has not the length of one."""
    length = list_or_int if isinstance(list_or_int, int) else len(list_or_int)
    return "es" * (length != 1)


# From Stack Overflow: https://stackoverflow.com/a/14693789/713980
# Placed at top level as to only compile it once
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def strip_ansi_codes(string, replace_with=""):
    """Strip ANSI colouring codes from a string to return plain text.

    From Stack Overflow: https://stackoverflow.com/a/14693789/713980
    """
    return ANSI_ESCAPE_RE.sub(replace_with, string)


def is_relative_to(path1, path2):
    """
    Checks if a path is relative to another.

    Should mimic Path.is_relative_to which not available in Python < 3.9

    path1 (Path | str): The path that could be a subpath
    path2 (Path | str): The path the could be the superpath
    """
    return str(path1).startswith(str(path2) + os.sep)


def file_md5(fname):
    """Calculates the md5sum for a file on the disk.

    Args:
        fname (str): Path to a local file.
    """

    # Calculate the md5 for the file on disk
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(io.DEFAULT_BUFFER_SIZE), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()


def validate_file_md5(file_name, expected_md5hex):
    """Validates the md5 checksum of a file on disk.

    Args:
        file_name (str): Path to a local file.
        expected (str): The expected md5sum.

    Raises:
        IOError, if the md5sum does not match the remote sum.
    """
    log.debug(f"Validating image hash: {file_name}")

    # Make sure the expected md5 sum is a hexdigest
    try:
        int(expected_md5hex, 16)
    except ValueError as ex:
        raise ValueError(f"The supplied md5 sum must be a hexdigest but it is {expected_md5hex}") from ex

    file_md5hex = file_md5(file_name)

    if file_md5hex.upper() == expected_md5hex.upper():
        log.debug(f"md5 sum of image matches expected: {expected_md5hex}")
    else:
        raise OSError(f"{file_name} md5 does not match remote: {expected_md5hex} - {file_md5hex}")

    return True


def nested_setitem(d, keys, value):
    """Sets the value in a nested dict using a list of keys to traverse

    Args:
        d (dict): the nested dictionary to traverse
        keys (list[Any]): A list of keys to iteratively traverse
        value (Any): The value to be set for the last key in the chain
    """
    current = d
    for k in keys[:-1]:
        current = current[k]
    current[keys[-1]] = value


def nested_delitem(d, keys):
    """Deletes a key from a nested dictionary

    Args:
        d (dict): the nested dictionary to traverse
        keys (list[Any]): A list of keys to iteratively traverse, deleting the final one
    """
    current = d
    for k in keys[:-1]:
        current = current[k]
    del current[keys[-1]]


@contextmanager
def set_wd(path: Path) -> Generator[None, None, None]:
    """Sets the working directory for this context.

    Arguments
    ---------

    path : Path
        Path to the working directory to be used inside this context.
    """
    start_wd = Path().absolute()
    os.chdir(Path(path).resolve())
    try:
        yield
    finally:
        os.chdir(start_wd)


@contextmanager
def set_wd_tempdir(base_dir: Path | None = None) -> Generator[Path, None, None]:
    """
    Context manager to create a tempdir and change into it, ensuring its removal and a return to
    the original working directory on exit (including exceptions).

    Args:
        base_dir: Directory in which to create the tempdir. Defaults to the system temp location.
    """
    with tempfile.TemporaryDirectory(dir=base_dir) as tmp, set_wd(Path(tmp)):
        yield Path(tmp)


def get_wf_files(wf_path: Path):
    """Return a list of all files in a directory (ignores .gitigore files)"""

    wf_files = []

    ignore = [".git/*"]
    try:
        with open(Path(wf_path, ".gitignore")) as f:
            for line in f.read().splitlines():
                if not line or line.startswith("#"):
                    continue
                # Make trailing-slash patterns match their entire subtree
                line = re.sub("/$", "/*", line)
                ignore.append(line)
    except FileNotFoundError:
        pass

    for path in Path(wf_path).rglob("*"):
        rpath = str(path.relative_to(wf_path))
        if any(fnmatch.fnmatch(rpath, pattern) for pattern in ignore):
            continue
        if path.is_file():
            wf_files.append(str(path))

    return wf_files
