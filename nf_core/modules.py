#!/usr/bin/env python
"""
Code to handle DSL2 module imports from a GitHub repository
"""

from __future__ import print_function

import base64
import logging
import os
import requests
import sys
import tempfile
import glob
import hashlib
import yaml
import shutil

log = logging.getLogger(__name__)


class ModulesRepo(object):
    """
    An object to store details about the repository being used for modules.

    Used by the `nf-core modules` top-level command with -r and -b flags,
    so that this can be used in the same way by all sucommands.
    """

    def __init__(self, repo="nf-core/modules", branch="master"):
        self.name = repo
        self.branch = branch


class PipelineModules(object):
    def __init__(self):
        """
        Initialise the PipelineModules object
        """
        self.modules_repo = ModulesRepo()
        self.pipeline_dir = None
        self.modules_file_tree = {}
        self.modules_current_hash = None
        self.modules_avail_module_names = []

    def list_modules(self):
        """
        Get available module names from GitHub tree for repo
        and print as list to stdout
        """
        self.get_modules_file_tree()
        return_str = ""

        if len(self.modules_avail_module_names) > 0:
            log.info("Modules available from {} ({}):\n".format(self.modules_repo.name, self.modules_repo.branch))
            # Print results to stdout
            return_str += "\n".join(self.modules_avail_module_names)
        else:
            log.info(
                "No available modules found in {} ({}):\n".format(self.modules_repo.name, self.modules_repo.branch)
            )
        return return_str

    def install(self, module):

        log.info("Installing {}".format(module))

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the available modules
        self.get_modules_file_tree()

        # Check that the supplied name is an available module
        if module not in self.modules_avail_module_names:
            log.error("Module '{}' not found in list of available modules.".format(module))
            log.info("Use the command 'nf-core modules list' to view available software")
            return False
        log.debug("Installing module '{}' at modules hash {}".format(module, self.modules_current_hash))

        # Check that we don't already have a folder for this module
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)
        if os.path.exists(module_dir):
            log.error("Module directory already exists: {}".format(module_dir))
            log.info("To update an existing module, use the commands 'nf-core update' or 'nf-core fix'")
            return False

        # Download module files
        files = self.get_module_file_urls(module)
        log.debug("Fetching module files:\n - {}".format("\n - ".join(files.keys())))
        for filename, api_url in files.items():
            dl_filename = os.path.join(self.pipeline_dir, "modules", "nf-core", filename)
            self.download_gh_file(dl_filename, api_url)
        log.info("Downloaded {} files to {}".format(len(files), module_dir))

    def update(self, module, force=False):
        log.error("This command is not yet implemented")
        pass

    def remove(self, module):
        """
        Remove an already installed module
        This command only works for modules that are installed from 'nf-core/modules'
        """
        log.info("Removing {}".format(module))

        # Check whether pipelines is valid
        self.has_valid_pipeline()

        # Get the module directory
        module_dir = os.path.join(self.pipeline_dir, "modules", "nf-core", "software", module)

        # Verify that the module is actually installed
        if not os.path.exists(module_dir):
            log.error("Module directory does not installed: {}".format(module_dir))
            log.info("The module you want to remove seems not to be installed. Is it a local module?")
            return False

        # Remove the module
        try:
            shutil.rmtree(module_dir)
            log.info("Successfully removed {} module".format(module))
            return True
        except OSError as e:
            log.error("Could not remove module: {}".format(e))
            return False

    def check_modules(self):
        log.error("This command is not yet implemented")
        pass

    def get_modules_file_tree(self):
        """
        Fetch the file list from the repo, using the GitHub API

        Sets self.modules_file_tree
             self.modules_current_hash
             self.modules_avail_module_names
        """
        api_url = "https://api.github.com/repos/{}/git/trees/{}?recursive=1".format(
            self.modules_repo.name, self.modules_repo.branch
        )
        r = requests.get(api_url)
        if r.status_code == 404:
            log.error(
                "Repository / branch not found: {} ({})\n{}".format(
                    self.modules_repo.name, self.modules_repo.branch, api_url
                )
            )
            sys.exit(1)
        elif r.status_code != 200:
            raise SystemError(
                "Could not fetch {} ({}) tree: {}\n{}".format(
                    self.modules_repo.name, self.modules_repo.branch, r.status_code, api_url
                )
            )

        result = r.json()
        assert result["truncated"] == False

        self.modules_current_hash = result["sha"]
        self.modules_file_tree = result["tree"]
        for f in result["tree"]:
            if f["path"].startswith("software/") and f["path"].endswith("/main.nf") and "/test/" not in f["path"]:
                # remove software/ and /main.nf
                self.modules_avail_module_names.append(f["path"][9:-8])

    def get_module_file_urls(self, module):
        """Fetch list of URLs for a specific module

        Takes the name of a module and iterates over the GitHub repo file tree.
        Loops over items that are prefixed with the path 'software/<module_name>' and ignores
        anything that's not a blob. Also ignores the test/ subfolder.

        Returns a dictionary with keys as filenames and values as GitHub API URIs.
        These can be used to then download file contents.

        Args:
            module (string): Name of module for which to fetch a set of URLs

        Returns:
            dict: Set of files and associated URLs as follows:

            {
                'software/fastqc/main.nf': 'https://api.github.com/repos/nf-core/modules/git/blobs/65ba598119206a2b851b86a9b5880b5476e263c3',
                'software/fastqc/meta.yml': 'https://api.github.com/repos/nf-core/modules/git/blobs/0d5afc23ba44d44a805c35902febc0a382b17651'
            }
        """
        results = {}
        for f in self.modules_file_tree:
            if not f["path"].startswith("software/{}".format(module)):
                continue
            if f["type"] != "blob":
                continue
            if "/test/" in f["path"]:
                continue
            results[f["path"]] = f["url"]
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
            raise SystemError("Could not fetch {} file: {}\n {}".format(self.modules_repo.name, r.status_code, api_url))
        result = r.json()
        file_contents = base64.b64decode(result["content"])

        # Write the file contents
        with open(dl_filename, "wb") as fh:
            fh.write(file_contents)

    def has_valid_pipeline(self):
        """Check that we were given a pipeline"""
        if self.pipeline_dir is None or not os.path.exists(self.pipeline_dir):
            log.error("Could not find pipeline: {}".format(self.pipeline_dir))
            return False
        main_nf = os.path.join(self.pipeline_dir, "main.nf")
        nf_config = os.path.join(self.pipeline_dir, "nextflow.config")
        if not os.path.exists(main_nf) and not os.path.exists(nf_config):
            log.error("Could not find a main.nf or nextfow.config file in: {}".format(self.pipeline_dir))
            return False


class ModulesTestHelper(object):
    def __init__(self, modules_dir=""):
        self.modules_dir = modules_dir
        self.file_dicts = []

    # Add custom dumper class to prevent overwriting the global state
    # This prevents yaml from changing the output order
    # See https://stackoverflow.com/a/52621703/1497385
    class CustomDumper(yaml.Dumper):
        def represent_dict_preserve_order(self, data):
            return self.represent_dict(data.items())

    CustomDumper.add_representer(dict, CustomDumper.represent_dict_preserve_order)

    def _md5(self, fname):
        """Generate md5 sum for file"""
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        md5sum = hash_md5.hexdigest()
        return md5sum

    def _get_md5_sums(self, dir, md5_sums=None):
        """
        Recursively go through directories and subdirectories
        and generate tuples of (<file_path>, <md5sum>)
        returns: list of tuples
        """
        if not md5_sums:
            md5_sums = []
        elements = glob.glob(dir + "/*")
        for elem in elements:
            # if file, get md5 sum
            if os.path.isfile(elem):
                elem_md5 = self._md5(elem)
                self.file_dicts.append({"path": elem, "md5sum": elem_md5})
            # if directory, apply recursion
            if os.path.isdir(elem):
                md5_sums = self._get_md5_sums(elem, md5_sums)

    def generate_test_yml(self):
        """
        Generate the test yml file
        """
        # Look for output directory
        output_dir = os.path.join(self.modules_dir, "output")
        try:
            assert os.path.exists(output_dir)
            assert len(glob.glob(os.path.join(output_dir, "*"))) > 0
        except:
            raise FileNotFoundError("Output directory doesn't exist or is empty")

        # Get list of files and their md5sums
        self._get_md5_sums(output_dir)

        yml_dict = [
            {
                "name": "<name of test>",
                "command": "<command here>",
                "tags": ["<tag>"],
                "files": self.file_dicts,
            }
        ]

        # print yaml to console
        print(yaml.dump(yml_dict, Dumper=self.CustomDumper))
