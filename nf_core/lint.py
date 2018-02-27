#!/usr/bin/env python
""" Linting code for the nf-core python package.

Tests Nextflow pipelines to check that they adhere to
the nf-core community guidelines.
"""

import click
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
        funcnames = ['check_files_exist', 'check_licence', 'check_pipeline']
        with click.progressbar(funcnames, label='Running pipeline tests') as fnames:
            for fname in fnames:
                getattr(self, fname)()

    def check_files_exist (self):
        """ Check a given pipeline directory for required files. """

        logging.debug('Checking required files exist')

        # NB: Should all be files, not directories
        # Supplying a list means if any are present it's a pass
        files_fail = [
            'nextflow.config',
            'Dockerfile',
            ['.travis.yml', 'circle.yml'],
            ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
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
        for files in files_fail:
            if not isinstance(files, list):
                files = [files]
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(files)))
            else:
                self.failed.append((1, "File not found: {}".format(files)))

        # Files that cause a warning
        for files in files_warn:
            if not isinstance(files, list):
                files = [files]
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(files)))
            else:
                self.warned.append((1, "File not found: {}".format(files)))


    def check_licence(self):
        logging.debug('Checking licence file is MIT')
        for l in ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md']:
            fn = os.path.join(self.path, l)
            if os.path.isfile(fn):
                if 'MIT' in open(fn).read():
                    self.passed.append((2, "Licence check passed"))
                    return
                else:
                    self.failed.append((2, "Licence file did not look like MIT: {}".format(fn)))
                    return
        self.failed.append((2, "Couldn't find MIT licence file"))


    def check_pipeline (self):
        """ Check a given pipeline for required config variables. """

        logging.debug('Checking pipeline config variables')

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
        try:
            with open(os.devnull, 'w') as devnull:
                nfconfig_raw = subprocess.check_output(['nextflow', 'config', self.path], stderr=devnull)
        except subprocess.CalledProcessError as e:
            print("ERROR: nextflow config returned non-zero error code: {},\n   {}".format(exc.returncode, exc.output))

        logging.debug("{} lines of pipeline config found!".format(len(nfconfig_raw.splitlines())))


    def print_results(self):
        # Print results
        logging.info("\n=================\n LINTING RESULTS\n=================\n")
        print("{0:>4} tests passed".format(len(self.passed)))
        print("{0:>4} tests had warnings".format(len(self.warned)))
        print("{0:>4} tests failed".format(len(self.failed)))
        if len(self.warned) > 0:
            print("\nWarnings:\n  {}".format("\n  ".join(["https://nf-core.github.io/errors#{}: {}".format(eid, msg) for eid, msg in self.warned])))
        if len(self.failed) > 0:
            print("\nFAILURES:\n  {}".format("\n  ".join(["https://nf-core.github.io/errors#{}: {}".format(eid, msg) for eid, msg in self.failed])))
        print("\n")
