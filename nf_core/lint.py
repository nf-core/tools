#!/usr/bin/env python
""" Linting code for the nf-core python package.

Tests Nextflow pipelines to check that they adhere to
the nf-core community guidelines.
"""

import logging
import os
import subprocess
import re
import yaml

import click

class PipelineLint(object):
    """ Object to hold linting info and results """

    def __init__(self, pipeline_dir):
        """ Initialise linting object """
        self.path = pipeline_dir
        self.files = []
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
        funcnames = [
            'check_files_exist',
            'check_licence',
            'check_docker',
            'check_config_vars',
            'check_ci_config',
            'check_readme'
        ]
        with click.progressbar(funcnames, label='Running pipeline tests') as fnames:
            for fname in fnames:
                getattr(self, fname)()
                if len(self.failed) > 0:
                    logging.info("\nFound test failures in '{}', halting lint run.".format(fname))
                    break

    def check_files_exist(self):
        """ Check a given pipeline directory for required files. """

        logging.debug('Checking required files exist')

        # NB: Should all be files, not directories
        # Supplying a list means if any are present it's a pass
        files_fail = [
            'nextflow.config',
            'Dockerfile',
            ['.travis.yml', '.circle.yml'],
            ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
            'README.md',
            'CHANGELOG.md',
            'docs/README.md',
            'docs/output.md',
            'docs/usage.md',
        ]
        files_warn = [
            'main.nf',
            'environment.yml',
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
                self.files.append(files)
            else:
                self.failed.append((1, "File not found: {}".format(files)))

        # Files that cause a warning
        for files in files_warn:
            if not isinstance(files, list):
                files = [files]
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(files)))
                self.files.append(files)
            else:
                self.warned.append((1, "File not found: {}".format(files)))


    def check_docker(self):
        """minimal tests only"""
        logging.debug('Checking Dockerfile')
        fn = os.path.join(self.path, "Dockerfile")
        content = ""
        with open(fn, 'r') as fh: content = fh.read()

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
                with open(fn, 'r') as fh: content = fh.read()

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


    def check_config_vars(self):
        """ Check a given pipeline for required config variables. """

        logging.debug('Checking pipeline config variables')

        # NB: Should all be files, not directories
        config_fail = [
            'params.version',
            'params.nf_required_version',
            'manifest.description',
            'manifest.homePage',
            'timeline.enabled',
            'trace.enabled',
            'report.enabled',
            'process.cpus',
            'process.memory',
            'process.time',
            'params.outdir'
        ]
        config_warn = [
            'manifest.mainScript',
            'timeline.file',
            'trace.file',
            'report.file',
            'process.container',
            'params.reads',
            'params.singleEnd'
        ]

        # Call `nextflow config` and pipe stderr to /dev/null
        try:
            with open(os.devnull, 'w') as devnull:
                nfconfig_raw = subprocess.check_output(['nextflow', 'config', '-flat', self.path], stderr=devnull)
        except subprocess.CalledProcessError as e:
            raise AssertionError("`nextflow config` returned non-zero error code: %s,\n   %s", e.returncode, e.output)
        else:
            for l in nfconfig_raw.splitlines():
                k, v = str(l).split(' = ', 1)
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


    def check_ci_config(self):
        """ Check that the Travis or Circle CI YAML config is valid """
        logging.debug('Checking continuous integration testing config')
        for cf in ['.travis.yml', 'circle.yml']:
            fn = os.path.join(self.path, cf)
            if os.path.isfile(fn):
                with open(fn, 'r') as fh:
                    ciconf = yaml.load(fh)
                # Check that the nf-core linting runs
                try:
                    assert('nf-core lint ${TRAVIS_BUILD_DIR}' in ciconf['script'])
                except AssertionError:
                    self.failed.append((5, "Continuous integration must run nf-core lint Tests: '{}'".format(fn)))
                else:
                    self.passed.append((5, "Continuous integration runs nf-core lint Tests: '{}'".format(fn)))
                # Check that we're testing the nf_required_version
                nf_required_version_tested = False
                for e in ciconf.get('env', []):
                    for s in e.split():
                        k,v = s.split('=')
                        if k == 'NXF_VER':
                            ci_ver = v.strip('\'"')
                            cv = self.config.get('params.nf_required_version', '').strip('\'"')
                            if ci_ver == cv:
                                nf_required_version_tested = True
                                self.passed.append((5, "Continuous integration checks minimum NF version: '{}'".format(fn)))
                if not nf_required_version_tested:
                    self.failed.append((5, "Continuous integration does not check minimum NF version: '{}'".format(fn)))


    def check_readme(self):
        """ Check the repository README file for errors """
        logging.debug('Checking the repository README')
        with open(os.path.join(self.path, 'README.md'), 'r') as fh:
            content = fh.read()

        # Check that there is a readme badge showing the minimum required version of Nextflow
        # and that it has the correct version
        nf_badge_re = r"\[!\[Nextflow\]\(https://img\.shields\.io/badge/nextflow-%E2%89%A5([\d\.]+)-brightgreen\.svg\)\]\(https://www\.nextflow\.io/\)"
        match = re.search(nf_badge_re, content)
        if match:
            nf_badge_version = match.group(1).strip('\'"')
            nf_config_version = self.config.get('params.nf_required_version').strip('\'"')
            try:
                assert nf_badge_version == nf_config_version
            except (AssertionError, KeyError) as e:
                self.failed.append((6, "README Nextflow minimum version badge does not match config. Badge: '{}', Config: '{}'".format(nf_badge_version, nf_config_version)))
            else:
                self.passed.append((6, "README Nextflow minimum version badge matched config. Badge: '{}', Config: '{}'".format(nf_badge_version, nf_config_version)))
        else:
            self.warned.append((6, "README did not have a Nextflow minimum version badge."))

        # Check that we have a bioconda badge if we have a bioconda environment file
        if 'environment.yml' in self.files:
            bioconda_badge = '[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](http://bioconda.github.io/)'
            if bioconda_badge in content:
                self.passed.append((6, "README had a bioconda badge"))
            else:
                self.failed.append((6, "Found a bioconda environment.yml file but no badge in the README"))


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
