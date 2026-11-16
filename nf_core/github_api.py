"""GitHub API session handling for the nf-core python package.

Kept separate from nf_core.utils so that requests_cache is only
imported when the GitHub API is actually used.
"""

import json
import logging
import os
import random
import re
import sys
import time
from pathlib import Path

import requests.auth
import requests_cache
import rich.console
import rich.markup
import yaml

from nf_core.utils import rich_force_colors, setup_requests_cachedir

log = logging.getLogger(__name__)


class GitHubAPISession(requests_cache.CachedSession):
    """
    Class to provide a single session for interacting with the GitHub API for a run.
    Inherits the requests_cache.CachedSession and adds additional functionality,
    such as automatically setting up GitHub authentication if we can.
    """

    def __init__(self) -> None:
        self.auth_mode: str | None = None
        self.return_ok: list[int] = [200, 201]
        self.return_retry: list[int] = [403]
        self.return_unauthorised: list[int] = [401]
        self.has_init: bool = False

    def lazy_init(self) -> None:
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
        gh_cli_config_fn = Path.home() / ".config" / "gh" / "hosts.yml"
        if self.auth is None and gh_cli_config_fn.exists():
            try:
                with open(gh_cli_config_fn) as fh:
                    gh_cli_config = yaml.safe_load(fh)
                    self.auth = requests.auth.HTTPBasicAuth(
                        gh_cli_config["github.com"]["user"],
                        gh_cli_config["github.com"]["oauth_token"],
                    )
                    self.auth_mode = f"gh CLI config: {gh_cli_config['github.com']['user']}"
            except (OSError, KeyError, yaml.YAMLError):
                ex_type, ex_value, _ = sys.exc_info()
                if ex_type is not None:
                    output = rich.markup.escape(f"{ex_type.__name__}: {ex_value}")
                    log.debug(f"Couldn't auto-auth with GitHub CLI auth from '{gh_cli_config_fn}': [red]{output}")

        # Default auth if we have a GitHub Token (eg. GitHub Actions CI)
        if os.environ.get("GITHUB_TOKEN") is not None and self.auth is None:
            self.auth_mode = "Bearer token with GITHUB_TOKEN"
            self.auth = BearerAuth(os.environ["GITHUB_TOKEN"])
        else:
            log.warning("Could not find GitHub authentication token. Some API requests may fail.")

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
        except (json.JSONDecodeError, TypeError) as e:
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
        if request.status_code in self.return_retry:
            stderr = rich.console.Console(stderr=True, force_terminal=rich_force_colors())
            try:
                r = self.request_retry(url)
            except Exception as e:
                stderr.print_exception()
                raise e
            else:
                return r
        elif request.status_code in self.return_unauthorised:
            raise RuntimeError("GitHub API PR failed, probably due to an expired GITHUB_TOKEN.")

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

        Used in nf-core pipelines sync code because we get 403 errors: too many simultaneous requests
        See https://github.com/nf-core/tools/issues/911
        """
        if not self.has_init:
            self.lazy_init()

        # Start the loop for a retry mechanism
        while True:
            # GET request
            if post_data is None:
                log.debug(f"Sending GET request to {url}")
                r = self.get(url=url)
            # POST request
            else:
                log.debug(f"Sending POST request to {url}")
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
gh_api = GitHubAPISession()
