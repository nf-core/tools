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
import shutil
import re
from datetime import datetime
from requests import exceptions

from requests.models import Response

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

    def create(self, directory, tool, subtool=None):
        """
        Create a new module from the template

        If <directory> is a ppipeline, this function creates a file in the
        'directory/modules/local/process' dir called <tool_subtool.nf>

        If <directory> is a clone of nf-core/modules, it creates the files and
        corresponding directories:

        modules/software/tool/subtool/
            * main.nf
            * meta.yml
            * functoins.nf

        modules/tests/software/tool/subtool/
            * main.nf
            * test.yml

        Additionally the necessary lines to run the tests are appended to
        modules/.github/filters.yml
        The function will also try to look for a bioconda package called 'tool'
        and for a matching container on quay.io

        :param directory:   the target directory to create the module template in
        :param tool:        name of the tool
        :param subtool:     name of the
        """
        template_urls = {
            "module.nf": "https://raw.githubusercontent.com/nf-core/modules/master/software/TOOL/SUBTOOL/main.nf",
            "functions.nf": "https://raw.githubusercontent.com/nf-core/modules/master/software/TOOL/SUBTOOL/functions.nf",
            "meta.yml": "https://raw.githubusercontent.com/nf-core/modules/master/software/TOOL/SUBTOOL/meta.yml",
            "test.yml": "https://raw.githubusercontent.com/nf-core/modules/master/tests/software/TOOL/SUBTOOL/test.yml",
            "test.nf": "https://raw.githubusercontent.com/nf-core/modules/master/tests/software/TOOL/SUBTOOL/main.nf",
        }
        # Check whether the given directory is a nf-core pipeline or a clone
        # of nf-core modules
        self.repo_type = self.get_repo_type(directory)

        # Determine the tool name
        tool_name = tool
        if subtool:
            tool_name += "_" + subtool

        # Try to find a bioconda package for 'tool'
        newest_version = None
        try:
            response = _bioconda_package(tool, full_dep=False)
            version = max(response["versions"])
            newest_version = "bioconda::" + tool + "=" + version
            log.info(f"Using bioconda package: {newest_version}")
        except (ValueError, LookupError) as e:
            log.info(f"Could not find bioconda package ({e})")

        # Try to get the container tag (only if bioconda package was found)
        container_tag = None
        if newest_version:
            try:
                container_tag = _get_container_tag(tool, version)
                log.info(f"Using docker/singularity container with tag: {tool}:{container_tag}")
            except (ValueError, LookupError) as e:
                log.info(f"Could not find a container tag ({e})")

        # Download and prepare the module.nf file
        module_nf = self.download_template(template_urls["module.nf"])
        module_nf = module_nf.replace("TOOL_SUBTOOL", tool_name.upper())

        # Add the bioconda package
        if newest_version:
            module_nf = module_nf.replace("bioconda::samtools=1.10", newest_version)
        # Add container
        if container_tag:
            module_nf = module_nf.replace(
                "https://depot.galaxyproject.org/singularity/samtools:1.10--h9402c20_2",
                f"https://depot.galaxyproject.org/singularity/{tool}:{container_tag}",
            )
            module_nf = module_nf.replace(
                "quay.io/biocontainers/samtools:1.10--h9402c20_2", f"quay.io/biocontainers/{tool}:{container_tag}"
            )

        # Create template for new module in nf-core pipeline
        if self.repo_type == "pipeline":
            module_file = os.path.join(directory, "modules", "local", "process", tool_name + ".nf")
            # Check whether module file already exists
            if os.path.exists(module_file):
                log.error(f"Module file {module_file} exists already!")
                return False

            # Create directories (if necessary) and the module .nf file
            try:
                os.makedirs(os.path.join(directory, "modules", "local", "process"), exist_ok=True)
                with open(module_file, "w") as fh:
                    fh.write(module_nf)

                # if functions.nf doesn't exist already, create it
                if not os.path.exists(os.path.join(directory, "modules", "local", "process", "functions.nf")):
                    functions_nf = self.download_template(template_urls["functions.nf"])
                    with open(os.path.join(directory, "modules", "local", "process", "functions.nf"), "w") as fh:
                        fh.write(functions_nf)

                log.info(f"Module successfully created: {module_file}")
                return True
            except OSError as e:
                log.error(f"Could not create module file {module_file}: {e}")
                return False

        # Create template for new module in nf-core/modules repository clone
        if self.repo_type == "modules":
            if subtool:
                tool_dir = os.path.join(directory, "software", tool, subtool)
                test_dir = os.path.join(directory, "tests", "software", tool, subtool)
            else:
                tool_dir = os.path.join(directory, "software", tool)
                test_dir = os.path.join(directory, "tests", "software", tool)
            if os.path.exists(tool_dir):
                log.error(f"Module directory {tool_dir} exists already!")
                return False
            if os.path.exists(test_dir):
                log.error(f"Module test directory {test_dir} exists already!")
                return False

            # Get the template copies of all necessary files
            functions_nf = self.download_template(template_urls["functions.nf"])
            meta_yml = self.download_template(template_urls["meta.yml"])
            test_yml = self.download_template(template_urls["test.yml"])
            test_nf = self.download_template(template_urls["test.nf"])

            # Replace TOOL/SUBTOOL
            if subtool:
                meta_yml = meta_yml.replace("subtool", subtool).replace("tool_", tool + "_")
                meta_yml = re.sub("^tool", tool, meta_yml)
                test_nf = test_nf.replace("SUBTOOL", subtool).replace("TOOL", tool)
                test_nf = test_nf.replace("tool_subtool", tool_name)
                test_nf = test_nf.replace("TOOL_SUBTOOL", tool_name.upper())
                test_yml = test_yml.replace("subtool", subtool).replace("tool_", tool + "_")
                test_yml = test_yml.replace("SUBTOOL", subtool).replace("TOOL", tool)
                test_yml = re.sub("tool", tool, test_yml)
            else:
                meta_yml = meta_yml.replace("tool subtool", tool_name).replace("tool_subtool", "")
                meta_yml = re.sub("^tool", tool_name, meta_yml)
                test_nf = (
                    test_nf.replace("TOOL_SUBTOOL", tool.upper()).replace("SUBTOOL/", "").replace("TOOL", tool.upper())
                )
                test_yml = test_yml.replace("tool subtool", tool_name).replace("tool_subtool", "")
                test_yml = re.sub("^tool", tool_name, test_yml)

            # Install main module files
            try:
                os.makedirs(tool_dir, exist_ok=True)
                # main.nf
                with open(os.path.join(tool_dir, "main.nf"), "w") as fh:
                    fh.write(module_nf)
                # meta.yml
                with open(os.path.join(tool_dir, "meta.yml"), "w") as fh:
                    fh.write(meta_yml)
                # functions.nf
                with open(os.path.join(tool_dir, "functions.nf"), "w") as fh:
                    fh.write(functions_nf)

                # Install test files
                os.makedirs(test_dir, exist_ok=True)
                # main.nf
                with open(os.path.join(test_dir, "main.nf"), "w") as fh:
                    fh.write(test_nf)
                # test.yml
                with open(os.path.join(test_dir, "test.yml"), "w") as fh:
                    fh.write(test_yml)
            except OSError as e:
                log.error(f"Could not create module files: {e}")
                return False

            # Add line to filters.yml
            try:
                with open(os.path.join(directory, ".github", "filters.yml"), "a") as fh:
                    if subtool:
                        content = (
                            "\n"
                            + f"{tool_name}:"
                            + "\n"
                            + f"  - software/{tool}/{subtool}/**"
                            + "\n"
                            + f"  - tests/software/{tool}/{subtool}/**\n"
                        )
                    else:
                        content = (
                            "\n"
                            + f"{tool_name}:"
                            + "\n"
                            + f"  - software/{tool}/**"
                            + "\n"
                            + f"  - tests/software/{tool}/**\n"
                        )
                    fh.write(content)

            except FileNotFoundError as e:
                log.error(f"Could not open filters.yml file!")
                return False

            log.info(f"Successfully created module files at: {tool_dir}")
            log.info(f"Added test files at: {test_dir}")
            return True

    def get_repo_type(self, directory):
        """
        Determine whether this is a pipeline repository or a clone of
        nf-core/modules
        """
        # Verify that the pipeline dir exists
        if dir is None or not os.path.exists(directory):
            log.error("Could not find directory: {}".format(directory))
            sys.exit(1)

        # Determine repository type
        if os.path.exists(os.path.join(directory, "main.nf")):
            return "pipeline"
        elif os.path.exists(os.path.join(directory, "software")):
            return "modules"
        else:
            log.error("Could not determine repository type of {}".format(directory))
            sys.exit(1)

    def download_template(self, url):
        """ Download the module template """

        r = requests.get(url=url)

        if r.status_code != 200:
            log.error("Could not download the template")
            sys.exit(1)
        else:
            try:
                template_copy = r.content.decode("ascii")
            except UnicodeDecodeError as e:
                log.error(f"Could not decode template file from {url}: {e}")
                sys.exit(1)

        return template_copy


def _bioconda_package(package, full_dep=True):
    """Query bioconda package information.
    Sends a HTTP GET request to the Anaconda remote API.
    Args:
        package (str): A bioconda package name.
    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """
    if full_dep:
        dep = package.split("::")[1]
        depname = dep.split("=")[0]
    else:
        depname = package

    anaconda_api_url = "https://api.anaconda.org/package/{}/{}".format("bioconda", depname)

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
            raise ValueError("Could not find `{}` in bioconda channel".format(package))


def _get_container_tag(package, version):
    """
    Given a biocnda package and version, look for a container
    at quay.io and return the tag of the most recent image
    that matches the package version
    Sends a HTTP GET request to the quay.io API.
    Args:
        package (str): A bioconda package name.
        version (str): Version of the bioconda package
    Raises:
        A LookupError, if the connection fails or times out or gives an unexpected status code
        A ValueError, if the package name can not be found (404)
    """

    quay_api_url = f"https://quay.io/api/v1/repository/biocontainers/{package}/tag/"

    try:
        response = requests.get(quay_api_url)
    except requests.exceptions.ConnectionError:
        raise LookupError("Could not connect to quay.io API")
    else:
        if response.status_code == 200:
            # Get the container tag
            tags = response.json()["tags"]
            matching_tags = [t for t in tags if t["name"].startswith(version)]
            # If version matches several images, get the most recent one, else return tag
            if len(matching_tags) > 0:
                tag = matching_tags[0]
                tag_date = _get_tag_date(tag["last_modified"])
                for t in matching_tags:
                    if _get_tag_date(t["last_modified"]) > tag_date:
                        tag = t
                return tag["name"]
            else:
                return matching_tags[0]["name"]
        elif response.status_code != 404:
            raise LookupError(
                f"quay.io API returned unexpected response code `{response.status_code}` for {quay_api_url}"
            )
        elif response.status_code == 404:
            raise ValueError(f"Could not find `{package}` on quayi.io/repository/biocontainers")


def _get_tag_date(tag_date):
    # Reformat a date given by quay.io to  datetime
    return datetime.strptime(tag_date.replace("-0000", "").strip(), "%a, %d %b %Y %H:%M:%S")
