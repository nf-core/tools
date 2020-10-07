#!/usr/bin/env python
"""Lists software licences for a given workflow."""

from __future__ import print_function

import logging
import json
import os
import re
import requests
import sys
import tabulate
import yaml
import rich.console
import rich.table

import nf_core.lint

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
            env_filename = os.path.join(self.pipeline, "environment.yml")
            if not os.path.exists(self.pipeline):
                raise LookupError("Pipeline {} exists, but no environment.yml file found".format(self.pipeline))
            with open(env_filename, "r") as fh:
                self.conda_config = yaml.safe_load(fh)
        else:
            env_url = "https://raw.githubusercontent.com/nf-core/{}/master/environment.yml".format(self.pipeline)
            log.debug("Fetching environment.yml file: {}".format(env_url))
            response = requests.get(env_url)
            # Check that the pipeline exists
            if response.status_code == 404:
                raise LookupError("Couldn't find pipeline nf-core/{}".format(self.pipeline))
            self.conda_config = yaml.safe_load(response.text)

    def fetch_conda_licences(self):
        """Fetch package licences from Anaconda and PyPi."""

        lint_obj = nf_core.lint.PipelineLint(self.pipeline)
        lint_obj.conda_config = self.conda_config
        # Check conda dependency list
        deps = lint_obj.conda_config.get("dependencies", [])
        log.info("Fetching licence information for {} tools".format(len(deps)))
        for dep in deps:
            try:
                if isinstance(dep, str):
                    lint_obj.check_anaconda_package(dep)
                elif isinstance(dep, dict):
                    lint_obj.check_pip_package(dep)
            except ValueError:
                log.error("Couldn't get licence information for {}".format(dep))

        for dep, data in lint_obj.conda_package_info.items():
            try:
                depname, depver = dep.split("=", 1)
                licences = set()
                # Licence for each version
                for f in data["files"]:
                    if not depver or depver == f.get("version"):
                        try:
                            licences.add(f["attrs"]["license"])
                        except KeyError:
                            pass
                # Main licence field
                if len(list(licences)) == 0 and isinstance(data["license"], str):
                    licences.add(data["license"])
                self.conda_package_licences[dep] = self.clean_licence_names(list(licences))
            except KeyError:
                pass

    def clean_licence_names(self, licences):
        """Normalises varying licence names.

        Args:
            licences (list): A list of licences which are basically raw string objects from
                the licence content information.

        Returns:
            list: Cleaned licences.
        """
        clean_licences = []
        for l in licences:
            l = re.sub(r"GNU General Public License v\d \(([^\)]+)\)", r"\1", l)
            l = re.sub(r"GNU GENERAL PUBLIC LICENSE", "GPL", l, flags=re.IGNORECASE)
            l = l.replace("GPL-", "GPLv")
            l = re.sub(r"GPL(\d)", r"GPLv\1", l)
            l = re.sub(r"GPL \(([^\)]+)\)", r"GPL \1", l)
            l = re.sub(r"GPL\s*v", "GPLv", l)
            l = re.sub(r"\s*(>=?)\s*(\d)", r" \1\2", l)
            clean_licences.append(l)
        return clean_licences

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
