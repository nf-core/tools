#!/usr/bin/env python
"""Lists available nf-core pipelines and versions."""

from __future__ import print_function
from collections import OrderedDict

import click
import datetime
import errno
import json
import logging
import os
import re
import subprocess
import sys

import git
import requests
import tabulate

import nf_core.utils

# Set up local caching for requests to speed up remote queries
nf_core.utils.setup_requests_cachedir()


def list_workflows(filter_by=None, sort_by='release', as_json=False):
    """Prints out a list of all nf-core workflows.

    Args:
        filter_by (list): A list of strings that can be used for filtering.
        sort_by (str): workflows can be sorted by keywords. Keyword must be one of
            `release` (default), `name`, `stars`.
        as_json (boolean): Set to true, if the lists should be printed in JSON.
    """
    wfs = Workflows(filter_by, sort_by)
    wfs.get_remote_workflows()
    wfs.get_local_nf_workflows()
    wfs.compare_remote_local()
    if as_json:
        wfs.print_json()
    else:
        wfs.print_summary()


class Workflows(object):
    """Workflow container class.

    Is used to collect local and remote nf-core pipelines. Pipelines
    can be sorted, filtered and compared.

    Args:
        filter_by (list): A list of strings that can be used for filtering.
        sort_by (str): workflows can be sorted by keywords. Keyword must be one of
            `release` (default), `name`, `stars`.
    """
    def __init__(self, filter_by=None, sort_by='release'):
        self.remote_workflows = list()
        self.local_workflows = list()
        self.local_unmatched = list()
        self.keyword_filters = filter_by if filter_by is not None else []
        self.sort_workflows_by = sort_by

    def get_remote_workflows(self):
        """Retrieves remote workflows from `nf-co.re <http://nf-co.re>`_.

        Remote workflows are stored in :attr:`self.remote_workflows` list.
        """
        # List all repositories at nf-core
        logging.debug("Fetching list of nf-core workflows")
        nfcore_url = 'http://nf-co.re/pipelines.json'
        response = requests.get(nfcore_url, timeout=10)
        if response.status_code == 200:
            repos = response.json()['remote_workflows']
            for repo in repos:
                self.remote_workflows.append(RemoteWorkflow(repo))

    def get_local_nf_workflows(self):
        """Retrieves local Nextflow workflows.

        Local workflows are stored in :attr:`self.local_workflows` list.
        """
        # Try to guess the local cache directory (much faster than calling nextflow)
        if os.environ.get('NXF_ASSETS'):
            nf_wfdir = os.path.join(os.environ.get('NXF_ASSETS'), 'nf-core')
        else:
            nf_wfdir = os.path.join(os.getenv("HOME"), '.nextflow', 'assets', 'nf-core')
        if os.path.isdir(nf_wfdir):
            logging.debug("Guessed nextflow assets directory - pulling nf-core dirnames")
            for wf_name in os.listdir(nf_wfdir):
                self.local_workflows.append( LocalWorkflow('nf-core/{}'.format(wf_name)) )

        # Fetch details about local cached pipelines with `nextflow list`
        else:
            logging.debug("Getting list of local nextflow workflows")
            try:
                with open(os.devnull, 'w') as devnull:
                    nflist_raw = subprocess.check_output(['nextflow', 'list'], stderr=devnull)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
            except subprocess.CalledProcessError as e:
                raise AssertionError("`nextflow list` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
            else:
                for wf_name in nflist_raw.splitlines():
                    if not str(wf_name).startswith('nf-core/'):
                        self.local_unmatched.append(wf_name)
                    else:
                        self.local_workflows.append( LocalWorkflow(wf_name) )

        # Find additional information about each workflow by checking its git history
        logging.debug("Fetching extra info about {} local workflows".format(len(self.local_workflows)))
        for wf in self.local_workflows:
            wf.get_local_nf_workflow_details()

    def compare_remote_local(self):
        """Matches local to remote workflows.

        If a matching remote workflow is found, the local workflow's Git commit hash is compared
        with the latest one from remote.

        A boolean flag in :attr:`RemoteWorkflow.local_is_latest` is set to True, if the local workflow
        is the latest.
        """
        for rwf in self.remote_workflows:
            for lwf in self.local_workflows:
                if rwf.full_name == lwf.full_name:
                    rwf.local_wf = lwf
                    if rwf.releases:
                        if rwf.releases[-1]['tag_sha'] == lwf.commit_sha:
                            rwf.local_is_latest = True
                        else:
                            rwf.local_is_latest = False

    def filtered_workflows(self):
        """Filters remote workflows for keywords.

        Returns:
            list: Filtered remote workflows.
        """
        # If no keywords, don't filter
        if not self.keyword_filters:
            return self.remote_workflows

        filtered_workflows = []
        for wf in self.remote_workflows:
            for k in self.keyword_filters:
                in_name = k in wf.name
                in_desc = k in wf.description
                in_topics = any([ k in t for t in wf.topics])
                if not in_name and not in_desc and not in_topics:
                    break
            else:
                # We didn't hit a break, so all keywords were found
                filtered_workflows.append(wf)
        return filtered_workflows

    def print_summary(self):
        """Prints a summary of all pipelines."""

        filtered_workflows = self.filtered_workflows()

        # Sort by released / dev, then alphabetical
        if not self.sort_workflows_by or self.sort_workflows_by == 'release':
            filtered_workflows.sort(
                key=lambda wf: (
                    (wf.releases[-1].get('published_at_timestamp', 0) if len(wf.releases) > 0 else 0) * -1,
                    wf.full_name.lower()
                )
            )
        # Sort by date pulled
        elif self.sort_workflows_by == 'pulled':
            def sort_pulled_date(wf):
                try:
                    return wf.local_wf.last_pull * -1
                except:
                    return 0
            filtered_workflows.sort(key=sort_pulled_date)
        # Sort by name
        elif self.sort_workflows_by == 'name':
            filtered_workflows.sort( key=lambda wf: wf.full_name.lower() )
        # Sort by stars, then name
        elif self.sort_workflows_by == 'stars':
            filtered_workflows.sort(
                key=lambda wf: (
                    wf.stargazers_count * -1,
                    wf.full_name.lower()
                )
            )

        # Build summary list to print
        summary = list()
        for wf in filtered_workflows:
            version = click.style(wf.releases[-1]['tag_name'], fg='blue') if len(wf.releases) > 0 else click.style('dev', fg='yellow')
            published = wf.releases[-1]['published_at_pretty'] if len(wf.releases) > 0 else '-'
            pulled = wf.local_wf.last_pull_pretty if wf.local_wf is not None else '-'
            if wf.local_wf is not None:
                is_latest = click.style('Yes', fg='green') if wf.local_is_latest else click.style('No', fg='red')
            else:
                is_latest = '-'
            rowdata = [ wf.full_name, version, published, pulled, is_latest ]
            if self.sort_workflows_by == 'stars':
                rowdata.insert(1, wf.stargazers_count)
            summary.append(rowdata)
        t_headers = ['Name', 'Version', 'Released', 'Last Pulled', 'Have latest release?']
        if self.sort_workflows_by == 'stars':
            t_headers.insert(1, 'Stargazers')

        # Print summary table
        print("", file=sys.stderr)
        print(tabulate.tabulate(summary, headers=t_headers))
        print("", file=sys.stderr)

    def print_json(self):
        """ Dump JSON of all parsed information """
        print(json.dumps({
            'local_workflows': self.local_workflows,
            'remote_workflows': self.remote_workflows
        }, default=lambda o: o.__dict__, indent=4))


class RemoteWorkflow(object):
    """A information container for a remote workflow.

    Args:
        data (dict): workflow information as they are retrieved from the Github repository REST API request
            (https://developer.github.com/v3/repos/#get).
    """

    def __init__(self, data):
        # Vars from the initial data payload
        self.name = data.get('name')
        self.full_name = data.get('full_name')
        self.description = data.get('description')
        self.topics = data.get('topics', [])
        self.archived = data.get('archived')
        self.stargazers_count = data.get('stargazers_count')
        self.watchers_count = data.get('watchers_count')
        self.forks_count = data.get('forks_count')

        # Placeholder vars for releases info
        self.releases = data.get('releases')

        # Placeholder vars for local comparison
        self.local_wf = None
        self.local_is_latest = None

        # Beautify date
        for release in self.releases:
            release['published_at_pretty'] = pretty_date(
                datetime.datetime.strptime(release.get('published_at'), "%Y-%m-%dT%H:%M:%SZ")
            )
            release['published_at_timestamp'] = int(datetime.datetime.strptime(release.get('published_at'), "%Y-%m-%dT%H:%M:%SZ").strftime("%s"))


class LocalWorkflow(object):
    """ Class to handle local workflows pulled by nextflow """

    def __init__(self, name):
        """ Initialise the LocalWorkflow object """
        self.full_name = name
        self.repository = None
        self.local_path = None
        self.commit_sha = None
        self.remote_url = None
        self.branch = None
        self.last_pull = None
        self.last_pull_date = None
        self.last_pull_pretty = None

    def get_local_nf_workflow_details(self):
        """ Get full details about a local cached workflow """

        if self.local_path is None:

            # Try to guess the local cache directory
            if os.environ.get('NXF_ASSETS'):
                nf_wfdir = os.path.join(os.environ.get('NXF_ASSETS'), self.full_name)
            else:
                nf_wfdir = os.path.join(os.getenv("HOME"), '.nextflow', 'assets', self.full_name)
            if os.path.isdir(nf_wfdir):
                logging.debug("Guessed nextflow assets workflow directory")
                self.local_path = nf_wfdir

            # Use `nextflow info` to get more details about the workflow
            else:
                try:
                    with open(os.devnull, 'w') as devnull:
                        nfinfo_raw = subprocess.check_output(['nextflow', 'info', '-d', self.full_name], stderr=devnull)
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        raise AssertionError("It looks like Nextflow is not installed. It is required for most nf-core functions.")
                except subprocess.CalledProcessError as e:
                    raise AssertionError("`nextflow list` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
                else:
                    re_patterns = {
                        'repository': r"repository\s*: (.*)",
                        'local_path': r"local path\s*: (.*)"
                    }
                    for key, pattern in re_patterns.items():
                        m = re.search(pattern, nfinfo_raw)
                        if m:
                            setattr(self, key, m.group(1))

        # Pull information from the local git repository
        if self.local_path is not None:
            try:
                repo = git.Repo(self.local_path)
                self.commit_sha = str(repo.head.commit.hexsha)
                self.remote_url = str(repo.remotes.origin.url)
                self.branch = str(repo.active_branch)
                self.last_pull = os.stat(os.path.join(self.local_path, '.git', 'FETCH_HEAD')).st_mtime
                self.last_pull_date = datetime.datetime.fromtimestamp(self.last_pull).strftime("%Y-%m-%d %H:%M:%S")
                self.last_pull_pretty = pretty_date(self.last_pull)
            except TypeError as e:
                logging.error(
                    "Could not fetch status of local Nextflow copy of {}:".format(self.full_name) +
                    "\n   {}".format(str(e)) +
                    "\n\nIt's probably a good idea to delete this local copy and pull again:".format(self.local_path) +
                    "\n   rm -rf {}".format(self.local_path) +
                    "\n   nextflow pull {}".format(self.full_name)
                )


def pretty_date(time):
    """Transforms a datetime object or a int() Epoch timestamp into a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc

    Based on https://stackoverflow.com/a/1551394/713980
    Adapted by sven1103
    """
    from datetime import datetime
    now = datetime.now()
    if isinstance(time, datetime):
        diff = now - time
    else:
        diff = now - datetime.fromtimestamp(time)
    second_diff = diff.seconds
    day_diff = diff.days

    pretty_msg = OrderedDict()
    pretty_msg[0] = [(float('inf'), 1, 'from the future')]
    pretty_msg[1] = [
            (10, 1, "just now"),
            (60, 1, "{sec:.0f} seconds ago"),
            (120, 1, "a minute ago"),
            (3600, 60, "{sec:.0f} minutes ago"),
            (7200, 1, "an hour ago"),
            (86400, 3600, "{sec:.0f} hours ago")
        ]
    pretty_msg[2] = [(float('inf'), 1, 'yesterday')]
    pretty_msg[7] = [(float('inf'), 1, '{days:.0f} day{day_s} ago')]
    pretty_msg[31] = [(float('inf'), 7, '{days:.0f} week{day_s} ago')]
    pretty_msg[365] = [(float('inf'), 30, '{days:.0f} months ago')]
    pretty_msg[float('inf')] = [(float('inf'), 365, '{days:.0f} year{day_s} ago')]

    for days, seconds in pretty_msg.items():
        if day_diff < days:
            for sec in seconds:
                if second_diff < sec[0]:
                    return sec[2].format(
                            days = day_diff/sec[1],
                            sec = second_diff/sec[1],
                            day_s = 's' if day_diff/sec[1] > 1 else ''
                        )
    return '... time is relative anyway'
