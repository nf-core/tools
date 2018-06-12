#!/usr/bin/env python
""" List software licences for a given workflow """

from __future__ import print_function

import logging
import json
import requests
import sys
import tabulate
import yaml

import nf_core.lint

class WorkflowLicences():
    """ Class to hold all licence info """

    def __init__(self, pipeline):
        """ Set class variables """
        self.pipeline = pipeline
        self.pipeline_licence = 'MIT'
        self.conda_package_licences = {}

    def fetch_conda_licences(self):
        """ Get the conda licences """
        env_url = 'https://raw.githubusercontent.com/nf-core/{}/master/environment.yml'.format(self.pipeline)
        response = requests.get(env_url)
        lint_obj = nf_core.lint.PipelineLint(self.pipeline)
        lint_obj.conda_config = yaml.load(response.text)
        # Check conda dependency list
        for dep in lint_obj.conda_config.get('dependencies', []):
            if isinstance(dep, str):
                try:
                    lint_obj.check_anaconda_package(dep)
                except ValueError:
                    print("Couldn't get {}".format(dep))
            elif isinstance(dep, dict):
                try:
                    lint_obj.check_pip_package(dep)
                except ValueError:
                    print("Couldn't get {}".format(dep))

        for dep, data in lint_obj.conda_package_info.items():
            try:
                self.conda_package_licences[dep] = data['license']
                if not isinstance(data['license'], basestring):
                    licences = set()
                    for f in data['files']:
                        try:
                            licences.add(f['attrs']['license'])
                        except KeyError:
                            pass
                    self.conda_package_licences[dep] = ', '.join(list(licences))
            except KeyError:
                pass

    def print_licences(self):
        """ Print the fetched information """
        logging.info("""Warning: This tool only prints licence information for the software tools packaged using conda.
        The pipeline may use other software and dependencies not described here. """)
        # Print summary table
        print("", file=sys.stderr)
        print(tabulate.tabulate([[d, l] for d, l in self.conda_package_licences.items()], headers=['Package Name', 'Licence']))
        print("", file=sys.stderr)
