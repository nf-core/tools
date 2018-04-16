#!/usr/bin/env python
""" List available nf-core pipelines and versions """

import json
import logging
import os
import subprocess
import requests


# 1 - Pull pipelines from GitHub, as with website
# 2 - Pull pipeline release info from GitHub
# 3 - Run `nextflow list` print currently cached pipeline names
# 4 - Try to `cd` to cached pipeline and run git commands to fetch:
#        last commit hash
#        full remote address
#        active branch
#        date of last pull - see https://stackoverflow.com/a/9229377/713980
# 5 - Compare commit to release info
# 6 - Print summary of all pipelines
#        name
#        latest release (with date?)
#        last pulled (NA if not pulled)
#        up to date (tick / cross)
#        local active branch?


# NOTES
#
# Write as much functionality as possible to work with functions
# that work on a single repository - can be reused for a `nf-core update`
# command. Ideas for function skeleton:
#
# get_remote_workflows
#   - list all repos and create a class object for each
#   - call https://api.github.com/orgs/nf-core/repos?per_page=100
# get_workflow_details
#   - Check object params and only execute if missing key vars
#   - call https://api.github.com/repos/nf-core/[name]
# get_workflow_releases
#   - if repo doesn't exist, get a "message": "Not Found"
#   - if repo exists but no releases, get an empty list
#   - if have releases, get a list of dicts with details
#   - compare dates, add flag `is_latest`
#   - call https://api.github.com/repos/nf-core/[name]/releases
#   - use tag_name to get the tag name of the latest release
#   - call https://api.github.com/repos/nf-core/[name]/tags/[tag_name]
#   - pull the commit sha
# get_local_nf_repos
#   - Run `nextflow list` to get all local workflows
#   - Filter for nf-core only? (maybe not)
#   - If we can, get all the info possible here, see https://github.com/nextflow-io/nextflow/issues/657
# get_local_nf_repo_details
#   - if needed, attempt to cd to the cache directory to scrape more information
# print_summary
#   - print a summary of what we've found
# print_json
#   - print JSON output of everything we've found


def list_workflows(json=False):
    """ Function to list all nf-core workflows """
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
        # print all local cached pipelines with `nextflow list`
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

    def compare_remote_local(self):
        pass

    def print_summary(self):
        pass

    def print_json(self):
        print(json.dumps([wf.__dict__ for wf in self.remote_workflows], indent=4))
        print(json.dumps([wf.__dict__ for wf in self.local_workflows], indent=4))


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

    def get_local_nf_workflow_details(self):
        pass
