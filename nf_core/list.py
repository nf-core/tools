#!/usr/bin/env python
""" List available nf-core pipelines and versions """

import datetime
import git
import json
import logging
import os
import subprocess
import re
import requests

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
        gh_api_url = 'https://api.github.com/orgs/nf-core/repos?per_page=100'
        response = requests.get(gh_api_url, timeout=10)
        if response.status_code == 200:
            gh_repos = response.json()
            for gh_repo in gh_repos:
                if gh_repo['name'] not in self.remote_ignore:
                    self.remote_workflows.append(RemoteWorkflow(gh_repo))

        # Get release information for each fetched workflow
        for wf in self.remote_workflows:
            wf.get_workflow_releases()

    def get_local_nf_workflows(self):
        """ Get local nextflow workflows """

        # Fetch details about local cached pipelines with `nextflow list`
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
        for wf in self.local_workflows:
            wf.get_local_nf_workflow_details()

    def compare_remote_local(self):
        pass

    def print_summary(self):
        """ Print summary of all pipelines """
        # - name
        # - latest release (with date?)
        # - last pulled (NA if not pulled)
        # - up to date (tick / cross)
        # - local active branch?
        pass

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
        self.latest_release = None
        self.latest_release_sha = None

        # Placeholder vars for local comparison
        self.is_local = None
        self.local_is_latest = None

    def get_workflow_releases(self):
        """ Fetch additional information about each release for a workflow """

        # Get information about every release
        gh_api_url = 'https://api.github.com/repos/{}/releases'.format(self.full_name)
        response = requests.get(gh_api_url, timeout=10)
        if response.status_code == 200:
            for rel in response.json():
                self.releases.append({
                    'name': rel.get('name'),
                    'published_at': rel.get('published_at'),
                    'tag_name': rel.get('tag_name'),
                    'tag_sha': None,
                    'draft': rel.get('draft'),
                    'prerelease': rel.get('prerelease'),
                })

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

    def get_local_nf_workflow_details(self):
        """ Get full details about a local cached workflow """

        # Use `nextflow info` to get more details about the workflow
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


        # Try to guess the local cache directory
        if self.local_path is None:
            nf_wfdir = os.path.join(os.getenv("HOME"), '.nextflow', 'assets', self.full_name)
            if os.path.isdir(nf_wfdir):
                self.local_path = nf_wfdir

        # Pull information from the local git repository
        if self.local_path is not None:
            repo = git.Repo(self.local_path)
            self.commit_sha = str(repo.head.commit.hexsha)
            self.remote_url = str(repo.remotes.origin.url)
            self.branch = str(repo.active_branch)
            self.last_pull = os.stat(os.path.join(self.local_path, '.git', 'FETCH_HEAD')).st_mtime
            self.last_pull_date = datetime.datetime.fromtimestamp(self.last_pull).strftime("%Y-%m-%d %H:%M:%S")
            self.last_pull_pretty = self.pretty_date(self.last_pull)

    def pretty_date(self, time):
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
