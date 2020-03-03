#!/usr/bin/env python
"""
Code to handle DSL2 module imports from nf-core/modules
"""

from __future__ import print_function

import base64
import logging
import os
import requests
import sys
import tempfile


class PipelineModules(object):

    def __init__(self):
        """
        Initialise the PipelineModules object
        """
        self.pipeline_dir = os.getcwd()
        self.modules_file_tree = {}
        self.modules_current_hash = None
        self.modules_avail_tool_names = []


    def list_modules(self):
        """
        Get available tool names from GitHub tree for nf-core/modules
        and print as list to stdout
        """
        mods = PipelineModules()
        mods.get_modules_file_tree()
        logging.info("Tools available from nf-core/modules:\n")
        # Print results to stdout
        print("\n".join(mods.modules_avail_tool_names))

    def install(self, tool):
        mods = PipelineModules()
        mods.get_modules_file_tree()

        # Check that the supplied name is an available tool
        if tool not in mods.modules_avail_tool_names:
            logging.error("Tool '{}' not found in list of available modules.".format(tool))
            logging.info("Use the command 'nf-core modules list' to view available tools")
            return
        logging.debug("Installing tool '{}' at modules hash {}".format(tool, mods.modules_current_hash))

        # Check that we don't already have a folder for this tool
        tool_dir = os.path.join(self.pipeline_dir, 'modules', 'tools', tool)
        if(os.path.exists(tool_dir)):
            logging.error("Tool directory already exists: {}".format(tool_dir))
            logging.info("To update an existing tool, use the commands 'nf-core update' or 'nf-core fix'")
            return

        # Download tool files
        files = mods.get_tool_file_urls(tool)
        logging.debug("Fetching tool files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            dl_filename = os.path.join(self.pipeline_dir, 'modules', filename)
            self.download_gh_file(dl_filename, api_url)

    def update(self, tool):
        mods = PipelineModules()
        mods.get_modules_file_tree()

    def remove(self, tool):
        pass

    def check_modules(self):
        pass

    def fix_modules(self):
        pass


    def get_modules_file_tree(self):
        """
        Fetch the file list from nf-core/modules, using the GitHub API

        Sets self.modules_file_tree
             self.modules_current_hash
             self.modules_avail_tool_names
        """
        r = requests.get("https://api.github.com/repos/nf-core/modules/git/trees/master?recursive=1")
        if r.status_code != 200:
            raise SystemError("Could not fetch nf-core/modules tree: {}".format(r.status_code))

        result = r.json()
        assert result['truncated'] == False

        self.modules_current_hash = result['sha']
        self.modules_file_tree = result['tree']
        for f in result['tree']:
            if f['path'].startswith('tools/') and f['path'].count('/') == 1:
                self.modules_avail_tool_names.append(f['path'].replace('tools/', ''))

    def get_tool_file_urls(self, tool):
        """Fetch list of URLs for a specific tool

        Takes the name of a tool and iterates over the GitHub nf-core/modules file tree.
        Loops over items that are prefixed with the path 'tools/<tool_name>' and ignores
        anything that's not a blob.

        Returns a dictionary with keys as filenames and values as GitHub API URIs.
        These can be used to then download file contents.

        Args:
            tool (string): Name of tool for which to fetch a set of URLs

        Returns:
            dict: Set of files and associated URLs as follows:

            {
                'tools/fastqc/main.nf': 'https://api.github.com/repos/nf-core/modules/git/blobs/65ba598119206a2b851b86a9b5880b5476e263c3',
                'tools/fastqc/meta.yml': 'https://api.github.com/repos/nf-core/modules/git/blobs/0d5afc23ba44d44a805c35902febc0a382b17651'
            }
        """
        results = {}
        for f in self.modules_file_tree:
            if f['path'].startswith('tools/{}'.format(tool)) and f['type'] == 'blob':
                results[f['path']] = f['url']
        return results

    def download_gh_file(self, dl_filename, api_url):
        """Download a file from GitHub using the GitHub API

        Args:
            dl_filename (string): Path to save file to
            api_url (string): GitHub API URL for file

        Raises:
            If a problem, raises an error
        """

        # Make target directory if it doesn't already exist
        dl_directory = os.path.dirname(dl_filename)
        if not os.path.exists(dl_directory):
            os.makedirs(dl_directory)

        # Call the GitHub API
        r = requests.get(api_url)
        if r.status_code != 200:
            raise SystemError("Could not fetch nf-core/modules file: {}\n {}".format(r.status_code, api_url))
        result = r.json()
        file_contents = base64.b64decode(result['content'])

        # Write the file contents
        with open(dl_filename, 'wb') as fh:
            fh.write(file_contents)
