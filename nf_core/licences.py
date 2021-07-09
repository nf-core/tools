#!/usr/bin/env python
"""Lists software licences for a given workflow."""

from __future__ import print_function

import logging
import json
import os
import re
import requests
import yaml
import rich.console
import rich.table

import nf_core.utils

log = logging.getLogger(__name__)


class WorkflowLicences(object):
    """A nf-core workflow licenses collection.

    Tries to retrieve the license information from all dependencies
    of a given nf-core pipeline.

    A condensed overview with license per dependency can be printed out.

    Args:
        pipeline (str): An existing nf-core pipeline name, like `nf-core/hlatyping`
            or short `hlatyping`.
    """

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.conda_config = None
        if self.pipeline.startswith("nf-core/"):
            self.pipeline = self.pipeline[8:]
        self.conda_packages = {}
        self.conda_package_licences = {}
        self.as_json = False

    def run_licences(self):
        """
        Run the nf-core licences action
        """
        self.get_environment_file()
        self.fetch_conda_licences()
        return self.print_licences()

    def get_environment_file(self):
        """Get the conda environment file for the pipeline"""
        if os.path.exists(self.pipeline):
            pipeline_obj = nf_core.utils.Pipeline(self.pipeline)
            pipeline_obj._load()
            if pipeline_obj._fp("environment.yml") not in pipeline_obj.files:
                raise LookupError(
                    "No `environment.yml` file found. (Note: DSL2 pipelines are currently not supported by this command.)"
                )
            self.conda_config = pipeline_obj.conda_config
        else:
            env_url = "https://raw.githubusercontent.com/nf-core/{}/master/environment.yml".format(self.pipeline)
            log.debug("Fetching environment.yml file: {}".format(env_url))
            response = requests.get(env_url)
            # Check that the pipeline exists
            if response.status_code == 404:
                raise LookupError(
                    f"Couldn't find pipeline conda file: {env_url}. (Note: DSL2 pipelines are currently not supported by this command.)"
                )
            self.conda_config = yaml.safe_load(response.text)

    def fetch_conda_licences(self):
        """Fetch package licences from Anaconda and PyPi."""

        # Check conda dependency list
        deps = self.conda_config.get("dependencies", [])
        deps_data = {}
        log.info("Fetching licence information for {} tools".format(len(deps)))
        for dep in deps:
            try:
                if isinstance(dep, str):
                    dep_channels = self.conda_config.get("channels", [])
                    deps_data[dep] = nf_core.utils.anaconda_package(dep, dep_channels)
                elif isinstance(dep, dict):
                    deps_data[dep] = nf_core.utils.pip_package(dep)
            except ValueError:
                log.error("Couldn't get licence information for {}".format(dep))

        for dep, data in deps_data.items():
            depname, depver = dep.split("=", 1)
            self.conda_package_licences[dep] = nf_core.utils.parse_anaconda_licence(data, depver)

    def print_licences(self):
        """Prints the fetched license information.

        Args:
            as_json (boolean): Prints the information in JSON. Defaults to False.
        """
        log.info("Warning: This tool only prints licence information for the software tools packaged using conda.")
        log.info("The pipeline may use other software and dependencies not described here. ")

        if self.as_json:
            return json.dumps(self.conda_package_licences, indent=4)
        else:
            table = rich.table.Table("Package Name", "Version", "Licence")
            licence_list = []
            for dep, licences in self.conda_package_licences.items():
                depname, depver = dep.split("=", 1)
                try:
                    depname = depname.split("::")[1]
                except IndexError:
                    pass
                licence_list.append([depname, depver, ", ".join(licences)])
            # Sort by licence, then package name
            licence_list = sorted(sorted(licence_list), key=lambda x: x[2])
            # Add table rows
            for lic in licence_list:
                table.add_row(*lic)
            return table
