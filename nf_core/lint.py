#!/usr/bin/env python
""" Linting code for the nf-core python package.

Tests Nextflow pipelines to check that they adhere to
the nf-core community guidelines.
"""

import logging
import os
import subprocess

import nf_core

class PipelineLint(object):
    """ Object to hold linting info and results """

    def __init__(self, pipeline_dir):
        """ Initialise linting object """
        self.path = pipeline_dir
        self.passed = []
        self.warned = []
        self.failed = []

    def lint_pipeline(self):
        """ Main linting function.

        Takes the pipeline directory as the primary input and iterates through
        the different linting checks in order. Collects any warnings or errors
        and returns summary at completion. Raises an exception if there is a
        critical error that makes the rest of the tests pointless (eg. no
        pipeline script). Results from this function are printed by the main script.

        Args:
            pipeline_dir (str): The path to the pipeline directory

        Returns:
            dict: Summary of test result messages structured as follows:
            {
                'pass': [
                    ( test-id (int), message (string) ),
                    ( test-id (int), message (string) )
                ],
                'warn': [(id, msg)],
                'fail': [(id, msg)],
            }

        Raises:
            If a critical problem is found, an AssertionError is raised.
        """

        self.check_files_exist()
        self.check_pipeline()

    def check_files_exist (self):
        """ Check a given pipeline directory for required files. """

        logging.info('Checking required files exist')

        # NB: Should all be files, not directories
        files_fail = [
            'nextflow.config',
            'Dockerfile',
            'LICENSE',
            'README.md',
            'CHANGELOG.md',
            'docs/README.md',
            'docs/output.md',
            'docs/usage.md',
        ]
        files_warn = [
            'main.nf',
            'conf/base.config',
            'tests/run_test.sh'
        ]

        def pf(file_path):
            return os.path.join(self.path, file_path)

        # First - critical files. Check that this is actually a Nextflow pipeline
        if not os.path.isfile(pf('nextflow.config')) and not os.path.isfile(pf('main.nf')):
            raise AssertionError('Neither nextflow.config or main.nf found! Is this a Nextflow pipeline?')

        # Files that cause an error
        for f in files_fail:
            if os.path.isfile(pf(f)):
                self.passed.append((1, "File found: {}".format(f)))
            else:
                self.failed.append((1, "File not found: {}".format(f)))

        # Files that cause a warning
        for f in files_warn:
            if os.path.isfile(pf(f)):
                self.passed.append((1, "File found: {}".format(f)))
            else:
                self.warned.append((1, "File not found: {}".format(f)))


    def check_pipeline (self):
        """ Check a given pipeline for required config variables. """

        logging.info('Checking pipeline config variables')

        # NB: Should all be files, not directories
        config_fail = [
            'manifest',
            'version',
        ]
        config_warn = [
            'timeline',
            'trace'
        ]

        # Call `nextflow config` and pipe stderr to /dev/null
        with open(os.devnull, 'w') as devnull:
            nfconfig_raw = subprocess.check_output(['nextflow', 'config', self.path], stderr=devnull)

        logging.info("{} lines of pipeline config found!".format(len(nfconfig_raw.splitlines())))


    def print_results(self):
        # Print results
        logging.info("\n=================\n LINTING RESULTS\n=================\n")
        print("{0:>4} tests passed".format(len(self.passed)))
        print("{0:>4} tests had warnings".format(len(self.warned)))
        print("{0:>4} tests failed".format(len(self.failed)))
        if len(self.warned) > 0:
            print("\nWarnings:\n  {}".format("\n  ".join(["https://nf-core.github.io/errors#{}: {}".format(id, msg) for id, msg in self.warned])))
        if len(self.failed) > 0:
            print("\nFailures:\n  {}".format("\n  ".join(["https://nf-core.github.io/errors#{}: {}".format(id, msg) for id, msg in self.failed])))
        print("\n")
