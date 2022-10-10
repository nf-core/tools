#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""
import datetime
import errno
import hashlib
import io
import json
import logging
import mimetypes
import os
import random
import re
import shlex
import subprocess
import sys
import time

import git
import prompt_toolkit
import questionary
import requests
import requests_cache
import rich
import yaml
from packaging.version import Version
from rich.live import Live
from rich.spinner import Spinner

import nf_core

log = logging.getLogger(__name__)

# Custom style for questionary
nfcore_question_style = prompt_toolkit.styles.Style(
    [
        ("qmark", "fg:ansiblue bold"),  # token in front of the question
        ("question", "bold"),  # question text
        ("answer", "fg:ansigreen nobold bg:"),  # submitted answer text behind the question
        ("pointer", "fg:ansiyellow bold"),  # pointer used in select and checkbox prompts
        ("highlighted", "fg:ansiblue bold"),  # pointed-at choice in select and checkbox prompts
        ("selected", "fg:ansiyellow noreverse bold"),  # style for a selected item of a checkbox
        ("separator", "fg:ansiblack"),  # separator in lists
        ("instruction", ""),  # user instructions for select, rawselect, checkbox
        ("text", ""),  # plain text
        ("disabled", "fg:gray italic"),  # disabled choices for select and checkbox prompts
        ("choice-default", "fg:ansiblack"),
        ("choice-default-changed", "fg:ansiyellow"),
        ("choice-required", "fg:ansired"),
    ]
)

NFCORE_CACHE_DIR = os.path.join(
    os.environ.get("XDG_CACHE_HOME", os.path.join(os.getenv("HOME"), ".cache")),
    "nfcore",
)
NFCORE_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME", os.path.join(os.getenv("HOME"), ".config")), "nfcore")


def check_if_outdated(current_version=None, remote_version=None, source_url="https://nf-co.re/tools_version"):
    """
    Check if the current version of nf-core is outdated
    """
    # Exit immediately if disabled via ENV var
    if os.environ.get("NFCORE_NO_VERSION_CHECK", False):
        return True
    # Set and clean up the current version string
    if current_version is None:
        current_version = nf_core.__version__
    current_version = re.sub(r"[^0-9\.]", "", current_version)
    # Build the URL to check against
    source_url = os.environ.get("NFCORE_VERSION_URL", source_url)
    source_url = f"{source_url}?v={current_version}"
    # Fetch and clean up the remote version
    if remote_version is None:
        response = requests.get(source_url, timeout=3)
        remote_version = re.sub(r"[^0-9\.]", "", response.text)
    # Check if we have an available update
    is_outdated = Version(remote_version) > Version(current_version)
    return (is_outdated, current_version, remote_version)


def rich_force_colors():
    """
    Check if any environment variables are set to force Rich to use coloured output
    """
    if os.getenv("GITHUB_ACTIONS") or os.getenv("FORCE_COLOR") or os.getenv("PY_COLORS"):
        return True
    return None


class Pipeline(object):
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

    def __init__(self, wf_path):
        """Initialise pipeline object"""
        self.conda_config = {}
        self.conda_package_info = {}
        self.nf_config = {}
        self.files = []
        self.git_sha = None
        self.minNextflowVersion = None
        self.wf_path = wf_path
        self.pipeline_name = None
        self.pipeline_prefix = None
        self.schema_obj = None

        try:
            repo = git.Repo(self.wf_path)
            self.git_sha = repo.head.object.hexsha
        except:
            log.debug(f"Could not find git hash for pipeline: {self.wf_path}")

        # Overwrite if we have the last commit from the PR - otherwise we get a merge commit hash
        if os.environ.get("GITHUB_PR_COMMIT", "") != "":
            self.git_sha = os.environ["GITHUB_PR_COMMIT"]

    def _load(self):
        """Run core load functions"""
        self._list_files()
        self._load_pipeline_config()
        self._load_conda_environment()

    def _list_files(self):
        """Get a list of all files in the pipeline"""
        try:
            # First, try to get the list of files using git
            git_ls_files = subprocess.check_output(["git", "ls-files"], cwd=self.wf_path).splitlines()
            self.files = []
            for fn in git_ls_files:
                full_fn = os.path.join(self.wf_path, fn.decode("utf-8"))
                if os.path.isfile(full_fn):
                    self.files.append(full_fn)
                else:
                    log.debug(f"`git ls-files` returned '{full_fn}' but could not open it!")
        except subprocess.CalledProcessError as e:
            # Failed, so probably not initialised as a git repository - just a list of all files
            log.debug(f"Couldn't call 'git ls-files': {e}")
            self.files = []
            for subdir, _, files in os.walk(self.wf_path):
                for fn in files:
                    self.files.append(os.path.join(subdir, fn))

    def _load_pipeline_config(self):
        """Get the nextflow config for this pipeline

        Once loaded, set a few convienence reference class attributes
        """
        self.nf_config = fetch_wf_config(self.wf_path)

        self.pipeline_prefix, self.pipeline_name = self.nf_config.get("manifest.name", "").strip("'").split("/")

        nextflowVersionMatch = re.search(r"[0-9\.]+(-edge)?", self.nf_config.get("manifest.nextflowVersion", ""))
        if nextflowVersionMatch:
            self.minNextflowVersion = nextflowVersionMatch.group(0)

    def _load_conda_environment(self):
        """Try to load the pipeline environment.yml file, if it exists"""
        try:
            with open(os.path.join(self.wf_path, "environment.yml"), "r") as fh:
                self.conda_config = yaml.safe_load(fh)
        except FileNotFoundError:
            log.debug("No conda `environment.yml` file found.")

    def _fp(self, fn):
        """Convenience function to get full path to a file in the pipeline"""
        return os.path.join(self.wf_path, fn)


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
        path = os.path.join(wf_path, fn)
        if not os.path.isfile(path):
            raise UserWarning(f"'{wf_path}' is not a pipeline - '{fn}' is missing")


def fetch_wf_config(wf_path, cache_config=True):
    """Uses Nextflow to retrieve the the configuration variables
    from a Nextflow workflow.

    Args:
        wf_path (str): Nextflow workflow file system path.
        cache_config (bool): cache configuration or not (def. True)

    Returns:
        dict: Workflow configuration settings.
    """

    log.debug(f"Got '{wf_path}' as path")

    config = {}
    cache_fn = None
    cache_basedir = None
    cache_path = None

    # Nextflow home directory - use env var if set, or default to ~/.nextflow
    nxf_home = os.environ.get("NXF_HOME", os.path.join(os.getenv("HOME"), ".nextflow"))

    # Build a cache directory if we can
    if os.path.isdir(nxf_home):
        cache_basedir = os.path.join(nxf_home, "nf-core")
        if not os.path.isdir(cache_basedir):
            os.mkdir(cache_basedir)

    # If we're given a workflow object with a commit, see if we have a cached copy
    cache_fn = None
    # Make a filename based on file contents
    concat_hash = ""
    for fn in ["nextflow.config", "main.nf"]:
        try:
            with open(os.path.join(wf_path, fn), "rb") as fh:
                concat_hash += hashlib.sha256(fh.read()).hexdigest()
        except FileNotFoundError:
            pass
    # Hash the hash
    if len(concat_hash) > 0:
        bighash = hashlib.sha256(concat_hash.encode("utf-8")).hexdigest()
        cache_fn = f"wf-config-cache-{bighash[:25]}.json"

    if cache_basedir and cache_fn:
        cache_path = os.path.join(cache_basedir, cache_fn)
        if os.path.isfile(cache_path):
            log.debug(f"Found a config cache, loading: {cache_path}")
            with open(cache_path, "r") as fh:
                config = json.load(fh)
            return config
    log.debug("No config cache found")

    # Call `nextflow config`
    nfconfig_raw = nextflow_cmd(f"nextflow config -flat {wf_path}")
    for l in nfconfig_raw.splitlines():
        ul = l.decode("utf-8")
        try:
            k, v = ul.split(" = ", 1)
            config[k] = v
        except ValueError:
            log.debug(f"Couldn't find key=value config pair:\n  {ul}")

    # Scrape main.nf for additional parameter declarations
    # Values in this file are likely to be complex, so don't both trying to capture them. Just get the param name.
    try:
        main_nf = os.path.join(wf_path, "main.nf")
        with open(main_nf, "r") as fh:
            for l in fh:
                match = re.match(r"^\s*(params\.[a-zA-Z0-9_]+)\s*=", l)
                if match:
                    config[match.group(1)] = "null"
    except FileNotFoundError as e:
        log.debug(f"Could not open {main_nf} to look for parameter declarations - {e}")

    # If we can, save a cached copy
    # HINT: during testing phase (in test_download, for example) we don't want
    # to save configuration copy in $HOME, otherwise the tests/test_download.py::DownloadTest::test_wf_use_local_configs
    # will fail after the first attempt. It's better to not save temporary data
    # in others folders than tmp when doing tests in general
    if cache_path and cache_config:
        log.debug(f"Saving config cache: {cache_path}")
        with open(cache_path, "w") as fh:
            json.dump(config, fh, indent=4)

    return config


def nextflow_cmd(cmd):
    """Run a Nextflow command and capture the output. Handle errors nicely"""
    try:
        nf_proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return nf_proc.stdout
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
    except subprocess.CalledProcessError as e:
        raise AssertionError(
            f"Command '{cmd}' returned non-zero error code '{e.returncode}':\n[red]> {e.stderr.decode()}{e.stdout.decode()}"
        )


def setup_nfcore_dir():
    """Creates a directory for files that need to be kept between sessions

    Currently only used for keeping local copies of modules repos
    """
    if not os.path.exists(NFCORE_DIR):
        os.makedirs(NFCORE_DIR)


def setup_requests_cachedir():
    """Sets up local caching for faster remote HTTP requests.

    Caching directory will be set up in the user's home directory under
    a .config/nf-core/cache_* subdir.

    Uses requests_cache monkey patching.
    Also returns the config dict so that we can use the same setup with a Session.
    """
    pyversion = ".".join(str(v) for v in sys.version_info[0:3])
    cachedir = os.path.join(NFCORE_CACHE_DIR, f"cache_{pyversion}")

    config = {
        "cache_name": os.path.join(cachedir, "github_info"),
        "expire_after": datetime.timedelta(hours=1),
        "backend": "sqlite",
    }

    logging.getLogger("requests_cache").setLevel(logging.WARNING)
    try:
        if not os.path.exists(cachedir):
            os.makedirs(cachedir)
        requests_cache.install_cache(**config)
    except PermissionError:
        pass

    return config


def wait_cli_function(poll_func, poll_every=20):
    """
    Display a command-line spinner while calling a function repeatedly.

    Keep waiting until that function returns True

    Arguments:
       poll_func (function): Function to call
       poll_every (int): How many tenths of a second to wait between function calls. Default: 20.

    Returns:
       None. Just sits in an infite loop until the function returns True.
    """
    try:
        spinner = Spinner("dots2", "Use ctrl+c to stop waiting and force exit.")
        with Live(spinner, refresh_per_second=20):
            while True:
                if poll_func():
                    break
                time.sleep(2)
    except KeyboardInterrupt:
        raise AssertionError("Cancelled!")


def poll_nfcore_web_api(api_url, post_data=None):
    """
    Poll the nf-core website API

    Takes argument api_url for URL

    Expects API reponse to be valid JSON and contain a top-level 'status' key.
    """
    # Run without requests_cache so that we get the updated statuses
    with requests_cache.disabled():
        try:
            if post_data is None:
                response = requests.get(api_url, headers={"Cache-Control": "no-cache"})
            else:
                response = requests.post(url=api_url, data=post_data)
        except requests.exceptions.Timeout:
            raise AssertionError(f"URL timed out: {api_url}")
        except requests.exceptions.ConnectionError:
            raise AssertionError(f"Could not connect to URL: {api_url}")
        else:
            if response.status_code != 200:
                log.debug(f"Response content:\n{response.content}")
                raise AssertionError(
                    f"Could not access remote API results: {api_url} (HTML {response.status_code} Error)"
                )
            try:
                web_response = json.loads(response.content)
                if "status" not in web_response:
                    raise AssertionError()
            except (json.decoder.JSONDecodeError, AssertionError, TypeError):
                log.debug(f"Response content:\n{response.content}")
                raise AssertionError(
                    f"nf-core website API results response not recognised: {api_url}\n "
                    "See verbose log for full response"
                )
            else:
                return web_response


class GitHub_API_Session(requests_cache.CachedSession):
    """
    Class to provide a single session for interacting with the GitHub API for a run.
    Inherits the requests_cache.CachedSession and adds additional functionality,
    such as automatically setting up GitHub authentication if we can.
    """

    def __init__(self):  # pylint: disable=super-init-not-called
        self.auth_mode = None
        self.return_ok = [200, 201]
        self.return_retry = [403]
        self.has_init = False

    def lazy_init(self):
        """
        Initialise the object.

        Only do this when it's actually being used (due to global import)
        """
        log.debug("Initialising GitHub API requests session")
        cache_config = setup_requests_cachedir()
        super().__init__(**cache_config)
        self.setup_github_auth()
        self.has_init = True

    def setup_github_auth(self, auth=None):
        """
        Try to automatically set up GitHub authentication
        """
        if auth is not None:
            self.auth = auth
            self.auth_mode = "supplied to function"

        # Class for Bearer token authentication
        # https://stackoverflow.com/a/58055668/713980
        class BearerAuth(requests.auth.AuthBase):
            def __init__(self, token):
                self.token = token

            def __call__(self, r):
                r.headers["authorization"] = f"Bearer {self.token}"
                return r

        # Default auth if we're running and the gh CLI tool is installed
        gh_cli_config_fn = os.path.expanduser("~/.config/gh/hosts.yml")
        if self.auth is None and os.path.exists(gh_cli_config_fn):
            try:
                with open(gh_cli_config_fn, "r") as fh:
                    gh_cli_config = yaml.safe_load(fh)
                    self.auth = requests.auth.HTTPBasicAuth(
                        gh_cli_config["github.com"]["user"], gh_cli_config["github.com"]["oauth_token"]
                    )
                    self.auth_mode = f"gh CLI config: {gh_cli_config['github.com']['user']}"
            except Exception:
                ex_type, ex_value, _ = sys.exc_info()
                output = rich.markup.escape(f"{ex_type.__name__}: {ex_value}")
                log.debug(f"Couldn't auto-auth with GitHub CLI auth from '{gh_cli_config_fn}': [red]{output}")

        # Default auth if we have a GitHub Token (eg. GitHub Actions CI)
        if os.environ.get("GITHUB_TOKEN") is not None and self.auth is None:
            self.auth_mode = "Bearer token with GITHUB_TOKEN"
            self.auth = BearerAuth(os.environ["GITHUB_TOKEN"])

        log.debug(f"Using GitHub auth: {self.auth_mode}")

    def log_content_headers(self, request, post_data=None):
        """
        Try to dump everything to the console, useful when things go wrong.
        """
        log.debug(f"Requested URL: {request.url}")
        log.debug(f"From requests cache: {request.from_cache}")
        log.debug(f"Request status code: {request.status_code}")
        log.debug(f"Request reason: {request.reason}")
        if post_data is None:
            post_data = {}
        try:
            log.debug(json.dumps(dict(request.headers), indent=4))
            log.debug(json.dumps(request.json(), indent=4))
            log.debug(json.dumps(post_data, indent=4))
        except Exception as e:
            log.debug(f"Could not parse JSON response from GitHub API! {e}")
            log.debug(request.headers)
            log.debug(request.content)
            log.debug(post_data)

    def safe_get(self, url):
        """
        Run a GET request, raise a nice exception with lots of logging if it fails.
        """
        if not self.has_init:
            self.lazy_init()
        request = self.get(url)
        if request.status_code not in self.return_ok:
            self.log_content_headers(request)
            raise AssertionError(f"GitHub API PR failed - got return code {request.status_code} from {url}")
        return request

    def get(self, url, **kwargs):
        """
        Initialise the session if we haven't already, then call the superclass get method.
        """
        if not self.has_init:
            self.lazy_init()
        return super().get(url, **kwargs)

    def request_retry(self, url, post_data=None):
        """
        Try to fetch a URL, keep retrying if we get a certain return code.

        Used in nf-core sync code because we get 403 errors: too many simultaneous requests
        See https://github.com/nf-core/tools/issues/911
        """
        if not self.has_init:
            self.lazy_init()

        # Start the loop for a retry mechanism
        while True:
            # GET request
            if post_data is None:
                log.debug(f"Seding GET request to {url}")
                r = self.get(url=url)
            # POST request
            else:
                log.debug(f"Seding POST request to {url}")
                r = self.post(url=url, json=post_data)

            # Failed but expected - try again
            if r.status_code in self.return_retry:
                self.log_content_headers(r, post_data)
                log.debug(f"GitHub API PR failed - got return code {r.status_code}")
                wait_time = float(re.sub("[^0-9]", "", str(r.headers.get("Retry-After", 0))))
                if wait_time == 0:
                    log.debug("Couldn't find 'Retry-After' header, guessing a length of time to wait")
                    wait_time = random.randrange(10, 60)
                log.warning(f"Got API return code {r.status_code}. Trying again after {wait_time} seconds..")
                time.sleep(wait_time)

            # Unexpected error - raise
            elif r.status_code not in self.return_ok:
                self.log_content_headers(r, post_data)
                raise RuntimeError(f"GitHub API PR failed - got return code {r.status_code} from {url}")

            # Success!
            else:
                return r


# Single session object to use for entire codebase. Not sure if there's a better way to do this?
gh_api = GitHub_API_Session()


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

    if dep_channels is None:
        dep_channels = ["conda-forge", "bioconda", "defaults"]

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
        except requests.exceptions.Timeout:
            raise LookupError(f"Anaconda API timed out: {anaconda_api_url}")
        except requests.exceptions.ConnectionError:
            raise LookupError("Could not connect to Anaconda API")
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
            try:
                licences.add(f["attrs"]["license"])
            except KeyError:
                pass
    # Main licence field
    if len(list(licences)) == 0 and isinstance(anaconda_response["license"], str):
        licences.add(anaconda_response["license"])

    # Clean up / standardise licence names
    clean_licences = []
    for l in licences:
        l = re.sub(r"GNU General Public License v\d \(([^\)]+)\)", r"\1", l)
        l = re.sub(r"GNU GENERAL PUBLIC LICENSE", "GPL", l, flags=re.IGNORECASE)
        l = l.replace("GPL-", "GPLv")
        l = re.sub(r"GPL\s*([\d\.]+)", r"GPL v\1", l)  # Add v prefix to GPL version if none found
        l = re.sub(r"GPL\s*v(\d).0", r"GPL v\1", l)  # Remove superflous .0 from GPL version
        l = re.sub(r"GPL \(([^\)]+)\)", r"GPL \1", l)
        l = re.sub(r"GPL\s*v", "GPL v", l)  # Normalise whitespace to one space between GPL and v
        l = re.sub(r"\s*(>=?)\s*(\d)", r" \1\2", l)  # Normalise whitespace around >= GPL versions
        l = l.replace("Clause", "clause")  # BSD capitilisation
        l = re.sub(r"-only$", "", l)  # Remove superflous GPL "only" version suffixes
        clean_licences.append(l)
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
    pip_depname, _ = dep.split("=", 1)
    pip_api_url = f"https://pypi.python.org/pypi/{pip_depname}/json"
    try:
        response = requests.get(pip_api_url, timeout=10)
    except requests.exceptions.Timeout:
        raise LookupError(f"PyPI API timed out: {pip_api_url}")
    except requests.exceptions.ConnectionError:
        raise LookupError(f"PyPI API Connection error: {pip_api_url}")
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

    biocontainers_api_url = f"https://api.biocontainers.pro/ga4gh/trs/v2/tools/{package}/versions/{package}-{version}"

    def get_tag_date(tag_date):
        """
        Format a date given by the biocontainers API
        Given format: '2021-03-25T08:53:00Z'
        """
        return datetime.datetime.strptime(tag_date, "%Y-%m-%dT%H:%M:%SZ")

    try:
        response = requests.get(biocontainers_api_url)
    except requests.exceptions.ConnectionError:
        raise LookupError("Could not connect to biocontainers.pro API")
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
                            all_docker[match.group(1)] = {"date": get_tag_date(img["updated"]), "image": img}
                    elif img["image_type"] == "Singularity":
                        # Obtain version and build
                        match = re.search(r"(?::)+([A-Za-z\d\-_.]+)", img["image_name"])
                        if match is not None:
                            all_singularity[match.group(1)] = {"date": get_tag_date(img["updated"]), "image": img}
                # Obtain common builds from Docker and Singularity images
                common_keys = list(all_docker.keys() & all_singularity.keys())
                current_date = None
                for k in common_keys:
                    # Get the most recent common image
                    date = max(all_docker[k]["date"], all_docker[k]["date"])
                    if docker_image is None or current_date < date:
                        docker_image = all_docker[k]["image"]
                        singularity_image = all_singularity[k]["image"]
                        current_date = date
                return docker_image["image_name"], singularity_image["image_name"]
            except TypeError:
                raise LookupError(f"Could not find docker or singularity container for {package}")
        elif response.status_code != 404:
            raise LookupError(f"Unexpected response code `{response.status_code}` for {biocontainers_api_url}")
        elif response.status_code == 404:
            raise ValueError(f"Could not find `{package}` on api.biocontainers.pro")


def custom_yaml_dumper():
    """Overwrite default PyYAML output to make Prettier YAML linting happy"""

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
            return super(CustomDumper, self).increase_indent(flow=flow, indentless=False)

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
    _, file_extension = os.path.splitext(path)
    if file_extension in binary_extensions:
        return True

    # Try to detect binary files
    (ftype, encoding) = mimetypes.guess_type(path, strict=False)
    if encoding is not None or (ftype is not None and any(ftype.startswith(ft) for ft in binary_ftypes)):
        return True


def prompt_remote_pipeline_name(wfs):
    """Prompt for the pipeline name with questionary

    Args:
        wfs: A nf_core.list.Workflows() object, where get_remote_workflows() has been called.

    Returns:
        pipeline (str): GitHub repo - username/repo

    Raises:
        AssertionError, if pipeline cannot be found
    """

    pipeline = questionary.autocomplete(
        "Pipeline name:",
        choices=[wf.name for wf in wfs.remote_workflows],
        style=nfcore_question_style,
    ).unsafe_ask()

    # Check nf-core repos
    for wf in wfs.remote_workflows:
        if wf.full_name == pipeline or wf.name == pipeline:
            return wf.full_name

    # Non nf-core repo on GitHub
    if pipeline.count("/") == 1:
        try:
            gh_api.get(f"https://api.github.com/repos/{pipeline}")
        except Exception:
            # No repo found - pass and raise error at the end
            pass
        else:
            return pipeline

    log.info("Available nf-core pipelines: '{}'".format("', '".join([w.name for w in wfs.remote_workflows])))
    raise AssertionError(f"Not able to find pipeline '{pipeline}'")


def prompt_pipeline_release_branch(wf_releases, wf_branches):
    """Prompt for pipeline release / branch

    Args:
        wf_releases (array): Array of repo releases as returned by the GitHub API
        wf_branches (array): Array of repo branches, as returned by the GitHub API

    Returns:
        choice (str): Selected release / branch name
    """
    # Prompt user for release tag
    choices = []

    # Releases
    if len(wf_releases) > 0:
        for tag in map(lambda release: release.get("tag_name"), wf_releases):
            tag_display = [("fg:ansiblue", f"{tag}  "), ("class:choice-default", "[release]")]
            choices.append(questionary.Choice(title=tag_display, value=tag))

    # Branches
    for branch in wf_branches.keys():
        branch_display = [("fg:ansiyellow", f"{branch}  "), ("class:choice-default", "[branch]")]
        choices.append(questionary.Choice(title=branch_display, value=branch))

    if len(choices) == 0:
        return False

    return questionary.select("Select release / branch:", choices=choices, style=nfcore_question_style).unsafe_ask()


def get_repo_releases_branches(pipeline, wfs):
    """Fetches details of a nf-core workflow to download.

    Args:
        pipeline (str): GitHub repo username/repo
        wfs: A nf_core.list.Workflows() object, where get_remote_workflows() has been called.

    Returns:
        wf_releases, wf_branches (tuple): Array of releases, Array of branches

    Raises:
        LockupError, if the pipeline can not be found.
    """

    wf_releases = []
    wf_branches = {}

    # Repo is a nf-core pipeline
    for wf in wfs.remote_workflows:
        if wf.full_name == pipeline or wf.name == pipeline:

            # Set to full name just in case it didn't have the nf-core/ prefix
            pipeline = wf.full_name

            # Store releases and stop loop
            wf_releases = list(sorted(wf.releases, key=lambda k: k.get("published_at_timestamp", 0), reverse=True))
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
                wf_releases = list(sorted(rel_r.json(), key=lambda k: k.get("published_at_timestamp", 0), reverse=True))

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
    branch_response = gh_api.safe_get(f"https://api.github.com/repos/{pipeline}/branches")
    for branch in branch_response.json():
        if (
            branch["name"] != "TEMPLATE"
            and branch["name"] != "initial_commit"
            and not branch["name"].startswith("nf-core-template-merge")
        ):
            wf_branches[branch["name"]] = branch["commit"]["sha"]

    # Return pipeline again in case we added the nf-core/ prefix
    return pipeline, wf_releases, wf_branches


def load_tools_config(dir="."):
    """
    Parse the nf-core.yml configuration file

    Look for a file called either `.nf-core.yml` or `.nf-core.yaml`

    Also looks for the deprecated file `.nf-core-lint.yml/yaml` and issues
    a warning that this file will be deprecated in the future

    Returns the loaded config dict or False, if the file couldn't be loaded
    """
    tools_config = {}
    config_fn = os.path.join(dir, ".nf-core.yml")

    # Check if old config file is used
    old_config_fn_yml = os.path.join(dir, ".nf-core-lint.yml")
    old_config_fn_yaml = os.path.join(dir, ".nf-core-lint.yaml")

    if os.path.isfile(old_config_fn_yml) or os.path.isfile(old_config_fn_yaml):
        log.error(
            "Deprecated `nf-core-lint.yml` file found! The file will not be loaded. Please rename the file to `.nf-core.yml`."
        )
        return {}

    if not os.path.isfile(config_fn):
        config_fn = os.path.join(dir, ".nf-core.yaml")

    # Load the YAML
    try:
        with open(config_fn, "r") as fh:
            tools_config = yaml.safe_load(fh)
    except FileNotFoundError:
        log.debug(f"No tools config file found: {config_fn}")
        return {}
    if tools_config is None:
        # If the file is empty
        return {}
    return tools_config


def sort_dictionary(d):
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
        raise IOError(f"{file_name} md5 does not match remote: {expected_md5hex} - {file_md5hex}")

    return True
