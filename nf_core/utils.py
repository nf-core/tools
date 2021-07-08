#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""
import nf_core

from distutils import version
import datetime
import errno
import git
import hashlib
import json
import logging
import mimetypes
import os
import prompt_toolkit
import questionary
import re
import requests
import requests_cache
import shlex
import subprocess
import sys
import time
import yaml
from rich.live import Live
from rich.spinner import Spinner

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


def check_if_outdated(current_version=None, remote_version=None, source_url="https://nf-co.re/tools_version"):
    """
    Check if the current version of nf-core is outdated
    """
    # Exit immediately if disabled via ENV var
    if os.environ.get("NFCORE_NO_VERSION_CHECK", False):
        return True
    # Set and clean up the current version string
    if current_version == None:
        current_version = nf_core.__version__
    current_version = re.sub("[^0-9\.]", "", current_version)
    # Build the URL to check against
    source_url = os.environ.get("NFCORE_VERSION_URL", source_url)
    source_url = "{}?v={}".format(source_url, current_version)
    # Fetch and clean up the remote version
    if remote_version == None:
        response = requests.get(source_url, timeout=3)
        remote_version = re.sub("[^0-9\.]", "", response.text)
    # Check if we have an available update
    is_outdated = version.StrictVersion(remote_version) > version.StrictVersion(current_version)
    return (is_outdated, current_version, remote_version)


def rich_force_colors():
    """
    Check if any environment variables are set to force Rich to use coloured output
    """
    if os.getenv("GITHUB_ACTIONS") or os.getenv("FORCE_COLOR") or os.getenv("PY_COLORS"):
        return True
    return None


def github_api_auto_auth():
    try:
        with open(os.path.join(os.path.expanduser("~/.config/gh/hosts.yml")), "r") as fh:
            auth = yaml.safe_load(fh)
            log.debug("Auto-authenticating GitHub API as '@{}'".format(auth["github.com"]["user"]))
            return requests.auth.HTTPBasicAuth(auth["github.com"]["user"], auth["github.com"]["oauth_token"])
    except Exception as e:
        log.debug(f"Couldn't auto-auth for GitHub: [red]{e}")
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
        self.schema_obj = None

        try:
            repo = git.Repo(self.wf_path)
            self.git_sha = repo.head.object.hexsha
        except:
            log.debug("Could not find git hash for pipeline: {}".format(self.wf_path))

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
                    log.debug("`git ls-files` returned '{}' but could not open it!".format(full_fn))
        except subprocess.CalledProcessError as e:
            # Failed, so probably not initialised as a git repository - just a list of all files
            log.debug("Couldn't call 'git ls-files': {}".format(e))
            self.files = []
            for subdir, dirs, files in os.walk(self.wf_path):
                for fn in files:
                    self.files.append(os.path.join(subdir, fn))

    def _load_pipeline_config(self):
        """Get the nextflow config for this pipeline

        Once loaded, set a few convienence reference class attributes
        """
        self.nf_config = fetch_wf_config(self.wf_path)

        self.pipeline_name = self.nf_config.get("manifest.name", "").strip("'").replace("nf-core/", "")

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


def fetch_wf_config(wf_path):
    """Uses Nextflow to retrieve the the configuration variables
    from a Nextflow workflow.

    Args:
        wf_path (str): Nextflow workflow file system path.

    Returns:
        dict: Workflow configuration settings.
    """

    config = dict()
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
        except FileNotFoundError as e:
            pass
    # Hash the hash
    if len(concat_hash) > 0:
        bighash = hashlib.sha256(concat_hash.encode("utf-8")).hexdigest()
        cache_fn = "wf-config-cache-{}.json".format(bighash[:25])

    if cache_basedir and cache_fn:
        cache_path = os.path.join(cache_basedir, cache_fn)
        if os.path.isfile(cache_path):
            log.debug("Found a config cache, loading: {}".format(cache_path))
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
            log.debug("Couldn't find key=value config pair:\n  {}".format(ul))

    # Scrape main.nf for additional parameter declarations
    # Values in this file are likely to be complex, so don't both trying to capture them. Just get the param name.
    try:
        main_nf = os.path.join(wf_path, "main.nf")
        with open(main_nf, "r") as fh:
            for l in fh:
                match = re.match(r"^\s*(params\.[a-zA-Z0-9_]+)\s*=", l)
                if match:
                    config[match.group(1)] = "false"
    except FileNotFoundError as e:
        log.debug("Could not open {} to look for parameter declarations - {}".format(main_nf, e))

    # If we can, save a cached copy
    if cache_path:
        log.debug("Saving config cache: {}".format(cache_path))
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
            f"Command '{cmd}' returned non-zero error code '{e.returncode}':\n[red]> {e.stderr.decode()}"
        )


def setup_requests_cachedir():
    """Sets up local caching for faster remote HTTP requests.

    Caching directory will be set up in the user's home directory under
    a .nfcore_cache subdir.
    """
    pyversion = ".".join(str(v) for v in sys.version_info[0:3])
    cachedir = os.path.join(os.getenv("HOME"), os.path.join(".nfcore", "cache_" + pyversion))

    try:
        if not os.path.exists(cachedir):
            os.makedirs(cachedir)
        requests_cache.install_cache(
            os.path.join(cachedir, "github_info"),
            expire_after=datetime.timedelta(hours=1),
            backend="sqlite",
        )
    except PermissionError:
        pass


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
        with Live(spinner, refresh_per_second=20) as live:
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
        except (requests.exceptions.Timeout):
            raise AssertionError("URL timed out: {}".format(api_url))
        except (requests.exceptions.ConnectionError):
            raise AssertionError("Could not connect to URL: {}".format(api_url))
        else:
            if response.status_code != 200:
                log.debug("Response content:\n{}".format(response.content))
                raise AssertionError(
                    "Could not access remote API results: {} (HTML {} Error)".format(api_url, response.status_code)
                )
            else:
                try:
                    web_response = json.loads(response.content)
                    assert "status" in web_response
                except (json.decoder.JSONDecodeError, AssertionError, TypeError) as e:
                    log.debug("Response content:\n{}".format(response.content))
                    raise AssertionError(
                        "nf-core website API results response not recognised: {}\n See verbose log for full response".format(
                            api_url
                        )
                    )
                else:
                    return web_response


def anaconda_package(dep, dep_channels=["conda-forge", "bioconda", "defaults"]):
    """Query conda package information.

    Sends a HTTP GET request to the Anaconda remote API.

    Args:
        dep (str): A conda package name.
        dep_channels (list): list of conda channels to use

    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """

    # Check if each dependency is the latest available version
    if "=" in dep:
        depname, depver = dep.split("=", 1)
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
        anaconda_api_url = "https://api.anaconda.org/package/{}/{}".format(ch, depname)
        try:
            response = requests.get(anaconda_api_url, timeout=10)
        except (requests.exceptions.Timeout):
            raise LookupError("Anaconda API timed out: {}".format(anaconda_api_url))
        except (requests.exceptions.ConnectionError):
            raise LookupError("Could not connect to Anaconda API")
        else:
            if response.status_code == 200:
                return response.json()
            elif response.status_code != 404:
                raise LookupError(
                    "Anaconda API returned unexpected response code `{}` for: {}\n{}".format(
                        response.status_code, anaconda_api_url, response
                    )
                )
            elif response.status_code == 404:
                log.debug("Could not find `{}` in conda channel `{}`".format(dep, ch))
    else:
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
    pip_depname, pip_depver = dep.split("=", 1)
    pip_api_url = "https://pypi.python.org/pypi/{}/json".format(pip_depname)
    try:
        response = requests.get(pip_api_url, timeout=10)
    except (requests.exceptions.Timeout):
        raise LookupError("PyPI API timed out: {}".format(pip_api_url))
    except (requests.exceptions.ConnectionError):
        raise LookupError("PyPI API Connection error: {}".format(pip_api_url))
    else:
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError("Could not find pip dependency using the PyPI API: `{}`".format(dep))


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
                for img in images:
                    # Get most recent Docker and Singularity image
                    if img["image_type"] == "Docker":
                        modification_date = get_tag_date(img["updated"])
                        if not docker_image or modification_date > get_tag_date(docker_image["updated"]):
                            docker_image = img
                    if img["image_type"] == "Singularity":
                        modification_date = get_tag_date(img["updated"])
                        if not singularity_image or modification_date > get_tag_date(singularity_image["updated"]):
                            singularity_image = img
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

        def increase_indent(self, flow=False, *args, **kwargs):
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
    filename, file_extension = os.path.splitext(path)
    if file_extension in binary_extensions:
        return True

    # Try to detect binary files
    (ftype, encoding) = mimetypes.guess_type(path, strict=False)
    if encoding is not None or (ftype is not None and any([ftype.startswith(ft) for ft in binary_ftypes])):
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
    else:
        if pipeline.count("/") == 1:
            try:
                gh_response = requests.get(f"https://api.github.com/repos/{pipeline}")
                assert gh_response.json().get("message") != "Not Found"
            except AssertionError:
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
            rel_r = requests.get(f"https://api.github.com/repos/{pipeline}/releases")

            # Check that this repo existed
            try:
                assert rel_r.json().get("message") != "Not Found"
            except AssertionError:
                raise AssertionError(f"Not able to find pipeline '{pipeline}'")
            except AttributeError:
                # When things are working we get a list, which doesn't work with .get()
                wf_releases = list(sorted(rel_r.json(), key=lambda k: k.get("published_at_timestamp", 0), reverse=True))

                # Get release tag commit hashes
                if len(wf_releases) > 0:
                    # Get commit hash information for each release
                    tags_r = requests.get(f"https://api.github.com/repos/{pipeline}/tags")
                    for tag in tags_r.json():
                        for release in wf_releases:
                            if tag["name"] == release["tag_name"]:
                                release["tag_sha"] = tag["commit"]["sha"]

        else:
            log.info("Available nf-core pipelines: '{}'".format("', '".join([w.name for w in wfs.remote_workflows])))
            raise AssertionError(f"Not able to find pipeline '{pipeline}'")

    # Get branch information from github api - should be no need to check if the repo exists again
    branch_response = requests.get(f"https://api.github.com/repos/{pipeline}/branches")
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
            f"Deprecated `nf-core-lint.yml` file found! The file will not be loaded. Please rename the file to `.nf-core.yml`."
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

    return tools_config
