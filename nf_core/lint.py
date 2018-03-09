#!/usr/bin/env python
""" Linting code for the nf-core python package.

Tests Nextflow pipelines to check that they adhere to
the nf-core community guidelines.
"""

import logging
import os
import subprocess

import click

#import nf_core

class PipelineLint(object):
    """ Object to hold linting info and results """

    def __init__(self, pipeline_dir):
        """ Initialise linting object """
        self.path = pipeline_dir
        self.config = {}
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
        funcnames = ['check_files_exist', 'check_licence', 'check_pipeline', 'check_docker']
        with click.progressbar(funcnames, label='Running pipeline tests') as fnames:
            for fname in fnames:
                getattr(self, fname)()

    def check_files_exist(self):
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


    def check_docker(self):
        """minimal tests only"""
        logging.debug('Checking Dockerfile')
        fn = os.path.join(self.path, "Dockerfile")
        content = ""
        try:
            with open(fn, 'r') as fh: content = fh.read()
        except Exception as exc:
            logging.error("Dockerfile check failed.")
            logging.error(exc)

        # Implicitely also checks if empty.
        if 'FROM ' in content:
            self.passed.append((2, "Dockerfile check passed"))
            return

        self.failed.append((2, "Dockerfile check failed"))


    def check_licence(self):
        logging.debug('Checking licence file is MIT')
        for l in ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md']:
            fn = os.path.join(self.path, l)
            if os.path.isfile(fn):
                content = ""
                try:
                    with open(fn, 'r') as fh: content = fh.read()
                except Exception as e:
                    raise AssertionError("Could not open licence file: %s,\n   %s", e.returncode, e.output)

                # needs at least copyright, permission, notice and "as-is" lines
                nl = content.count("\n")
                if nl < 4:
                    self.failed.append((3, "Number of lines too small for a valid MIT license file: {}".format(fn)))
                    return

                # determine whether this is indeed an MIT
                # license. Most variations actually don't contain the
                # string MIT Searching for 'without restriction'
                # instead (a crutch).
                if not 'without restriction' in content:
                    self.failed.append((3, "Licence file did not look like MIT: {}".format(fn)))
                    return

                # check for placeholders present in
                # - https://choosealicense.com/licenses/mit/
                # - https://opensource.org/licenses/MIT
                # - https://en.wikipedia.org/wiki/MIT_License
                placeholders = set(['[year]', '[fullname]',
                                    '<YEAR>', '<COPYRIGHT HOLDER>',
                                    '<year>', '<copyright holders>'])
                if any([ph in content for ph in placeholders]):
                    self.failed.append((3, "Licence file contains placeholders: {}".format(fn)))
                    return

                self.passed.append((3, "Licence check passed"))
                return

        self.failed.append((3, "Couldn't find MIT licence file"))


    def check_pipeline(self):
        """ Check a given pipeline for required config variables. """

        logging.debug('Checking pipeline config variables')

        # NB: Should all be files, not directories
        config_fail = [
            'version',
            'nf_required_version',
            'manifest.description',
            'manifest.homePage',
            'timeline.enabled',
            'trace.enabled',
            'report.enabled',
        ]
        config_warn = [
            'manifest.mainScript',
            'timeline.file',
            'trace.file',
            'report.file',
        ]

        # Call `nextflow config` and pipe stderr to /dev/null
        try:
            with open(os.devnull, 'w') as devnull:
                nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', self.path], stderr=devnull)
        except subprocess.CalledProcessError as e:
            raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
        else:
            for l in nfconfig_raw.splitlines():
                k, v = l.split(' = ', 1)
                self.config[k] = v
            for cf in config_fail:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(cf)))
                else:
                    self.failed.append((4, "Config variable not found: {}".format(cf)))
            for cf in config_warn:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(cf)))
                else:
                    self.warned.append((4, "Config variable not found: {}".format(cf)))


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
