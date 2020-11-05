#!/usr/bin/env python
"""
Common utility functions for the nf-core python package.
"""
import nf_core
import datetime
import errno
import json
import hashlib
import logging
import os
import re
import requests
import requests_cache
import subprocess
import sys
import time
from distutils import version

log = logging.getLogger(__name__)


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

    # Build a cache directory if we can
    if os.path.isdir(os.path.join(os.getenv("HOME"), ".nextflow")):
        cache_basedir = os.path.join(os.getenv("HOME"), ".nextflow", "nf-core")
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

    # Call `nextflow config` and pipe stderr to /dev/null
    try:
        with open(os.devnull, "w") as devnull:
            nfconfig_raw = subprocess.check_output(["nextflow", "config", "-flat", wf_path], stderr=devnull)
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
    except subprocess.CalledProcessError as e:
        raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
    else:
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


def setup_requests_cachedir():
    """Sets up local caching for faster remote HTTP requests.

    Caching directory will be set up in the user's home directory under
    a .nfcore_cache subdir.
    """
    # Only import it if we need it
    import requests_cache

    pyversion = ".".join(str(v) for v in sys.version_info[0:3])
    cachedir = os.path.join(os.getenv("HOME"), os.path.join(".nfcore", "cache_" + pyversion))
    if not os.path.exists(cachedir):
        os.makedirs(cachedir)
    requests_cache.install_cache(
        os.path.join(cachedir, "github_info"),
        expire_after=datetime.timedelta(hours=1),
        backend="sqlite",
    )


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
        is_finished = False
        check_count = 0

        def spinning_cursor():
            while True:
                for cursor in "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏":
                    yield "{} Use ctrl+c to stop waiting and force exit. ".format(cursor)

        spinner = spinning_cursor()
        while not is_finished:
            # Write a new loading text
            loading_text = next(spinner)
            sys.stdout.write(loading_text)
            sys.stdout.flush()
            # Show the loading spinner every 0.1s
            time.sleep(0.1)
            # Wipe the previous loading text
            sys.stdout.write("\b" * len(loading_text))
            sys.stdout.flush()
            # Only check every 2 seconds, but update the spinner every 0.1s
            check_count += 1
            if check_count > poll_every:
                is_finished = poll_func()
                check_count = 0
    except KeyboardInterrupt:
        raise AssertionError("Cancelled!")


def poll_nfcore_web_api(api_url, post_data=None):
    """
    Poll the nf-core website API

    Takes argument api_url for URL

    Expects API reponse to be valid JSON and contain a top-level 'status' key.
    """
    # Clear requests_cache so that we get the updated statuses
    requests_cache.clear()
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
            except (json.decoder.JSONDecodeError, AssertionError) as e:
                log.debug("Response content:\n{}".format(response.content))
                raise AssertionError(
                    "nf-core website API results response not recognised: {}\n See verbose log for full response".format(
                        api_url
                    )
                )
            else:
                return web_response
