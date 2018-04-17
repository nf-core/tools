#!/usr/bin/env python
""" List available nf-core pipelines and versions """

from __future__ import print_function

import datetime
import git
import json
import logging
import os
import re
import requests
import requests_cache
import subprocess
import sys
import tabulate
import tempfile

# Set up local caching for requests to speed up remote queries
cachedir = os.path.join(tempfile.gettempdir(), 'nfcore_cache')
if not os.path.exists(cachedir):
    os.mkdir(cachedir)
requests_cache.install_cache(
    os.path.join(cachedir, 'nfcore_cache'),
    expire_after=datetime.timedelta(hours=1),
    backend='sqlite',
)

def list_workflows(json=False):
    """ Main function to list all nf-core workflows """
    wfs = Workflows()
    wfs.get_remote_workflows()
    wfs.get_local_nf_workflows()
    wfs.compare_remote_local()
    if json:
        wfs.print_json()
    else:
        wfs.print_summary()

class Workflows(object):
    """ Class to hold all workflows """

    def __init__(self):
        """ Initialise the class with empty placeholder vars """
        self.remote_workflows = list()
        self.local_workflows = list()
        self.local_unmatched = list()
        self.remote_ignore = [
            'cookiecutter',
            'nf-core.github.io',
            'tools',
            'logos',
            'test-datasets'
        ]

    def get_remote_workflows(self):
        """ Get remote nf-core workflows """

        # List all repositories at nf-core
        logging.debug("Fetching list of nf-core workflows")
        gh_api_url = 'https://api.github.com/orgs/nf-core/repos?per_page=100'
        response = requests.get(gh_api_url, timeout=10)
        if response.status_code == 200:
            gh_repos = response.json()
            for gh_repo in gh_repos:
                if gh_repo['name'] not in self.remote_ignore:
                    self.remote_workflows.append(RemoteWorkflow(gh_repo))

        # Get release information for each fetched workflow
        logging.debug("Fetching release information for {} workflows".format(len(self.remote_workflows)))
        for wf in self.remote_workflows:
            wf.get_workflow_releases()

    def get_local_nf_workflows(self):
        """ Get local nextflow workflows """

        # Try to guess the local cache directory (much faster than calling nextflow)
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
            except subprocess.CalledProcessError as e:
                raise AssertionError("`nextflow list` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
            else:
                for wf_name in nflist_raw.splitlines():
                    if not wf_name.startswith('nf-core/'):
                        self.local_unmatched.append(wf_name)
                    else:
                        self.local_workflows.append( LocalWorkflow(wf_name) )

        # Find additional information about each workflow by checking its git history
        logging.debug("Fetching extra info about {} local workflows".format(len(self.local_workflows)))
        for wf in self.local_workflows:
            wf.get_local_nf_workflow_details()

    def compare_remote_local(self):
        """ Match local to remote workflows. """
        for rwf in self.remote_workflows:
            for lwf in self.local_workflows:
                if rwf.full_name == lwf.full_name:
                    rwf.local_wf = lwf
                    try:
                        if rwf.releases[0]['tag_sha'] == lwf.commit_sha:
                            rwf.local_is_latest = True
                        else:
                            rwf.local_is_latest = False
                    except IndexError:
                        pass

    def print_summary(self):
        """ Print summary of all pipelines """

        # Sort by released / dev, then alphabetical
        self.remote_workflows.sort(key=lambda item:(len(item.releases) == 0, item.full_name.lower()))

        # Build summary list to print
        summary = list()
        for wf in self.remote_workflows:
            summary.append([
                wf.full_name,
                wf.releases[0]['tag_name'] if len(wf.releases) > 0 else 'dev',
                wf.releases[0]['published_at_pretty'] if len(wf.releases) > 0 else '-',
                wf.local_wf.last_pull_pretty if wf.local_wf is not None else '-',
                'Yes' if wf.local_is_latest else 'No'
            ])

        # Print summary table
        print("", file=sys.stderr)
        print(tabulate.tabulate(summary, headers=['Name', 'Version', 'Published', 'Last Pulled', 'Default local is latest release?']))
        print("", file=sys.stderr)

    def print_json(self):
        """ Dump JSON of all parsed information """
        print(json.dumps({
            'local_workflows': [wf.__dict__ for wf in self.local_workflows],
            'remote_workflows': [wf.__dict__ for wf in self.remote_workflows]
        }, indent=4))


class RemoteWorkflow(object):
    """ Class to hold a single workflow """

    def __init__(self, data):
        """ Initialise a workflow object from the GitHub API object """

        # Vars from the initial data payload
        self.name = data.get('name')
        self.full_name = data.get('full_name')
        self.description = data.get('description')
        self.archived = data.get('archived')
        self.stargazers_count = data.get('stargazers_count')
        self.watchers_count = data.get('watchers_count')
        self.forks_count = data.get('forks_count')

        # Placeholder vars for releases info
        self.releases = list()

        # Placeholder vars for local comparison
        self.local_wf = None
        self.local_is_latest = None

    def get_workflow_releases(self):
        """ Fetch additional information about each release for a workflow """

        # Get information about every release
        gh_api_url = 'https://api.github.com/repos/{}/releases'.format(self.full_name)
        response = requests.get(gh_api_url, timeout=10)
        if response.status_code == 200:
            for rel in response.json():
                d = dict()
                d['name'] = rel.get('name')
                d['published_at'] = rel.get('published_at')
                d['published_at_pretty'] = pretty_date(datetime.datetime.strptime(rel.get('published_at'), "%Y-%m-%dT%H:%M:%SZ"))
                d['tag_name'] = rel.get('tag_name')
                d['tag_sha'] = None
                d['draft'] = rel.get('draft')
                d['prerelease'] = rel.get('prerelease')
                self.releases.append(d)
        self.releases.sort(key=lambda item:item['published_at'], reverse=True)

        # Fetch tag information to get the commit hashes
        if len(self.releases) > 0:
            gh_api_url = 'https://api.github.com/repos/{}/tags'.format(self.full_name)
            response = requests.get(gh_api_url, timeout=10)
            if response.status_code == 200:
                for rel in self.releases:
                    for tag in response.json():
                        if rel['tag_name'] == tag.get('name'):
                            rel['tag_sha'] = tag.get('commit', {}).get('sha')



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
            nf_wfdir = os.path.join(os.getenv("HOME"), '.nextflow', 'assets', self.full_name)
            if os.path.isdir(nf_wfdir):
                logging.debug("Guessed nextflow assets workflow directory")
                self.local_path = nf_wfdir

            # Use `nextflow info` to get more details about the workflow
            else:
                try:
                    with open(os.devnull, 'w') as devnull:
                        nfinfo_raw = subprocess.check_output(['nextflow', 'info', '-d', self.full_name], stderr=devnull)
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
            repo = git.Repo(self.local_path)
            self.commit_sha = str(repo.head.commit.hexsha)
            self.remote_url = str(repo.remotes.origin.url)
            self.branch = str(repo.active_branch)
            self.last_pull = os.stat(os.path.join(self.local_path, '.git', 'FETCH_HEAD')).st_mtime
            self.last_pull_date = datetime.datetime.fromtimestamp(self.last_pull).strftime("%Y-%m-%d %H:%M:%S")
            self.last_pull_pretty = pretty_date(self.last_pull)

def pretty_date(time):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc

    Based on https://stackoverflow.com/a/1551394/713980
    """
    from datetime import datetime
    now = datetime.now()
    if isinstance(time, datetime):
        diff = now - time
    else:
        diff = now - datetime.fromtimestamp(time)
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"
