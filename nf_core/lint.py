#!/usr/bin/env python
"""Linting policy for nf-core pipeline projects.

Tests Nextflow-based pipelines to check that they adhere to
the nf-core community guidelines.
"""

import logging
import io
import os
import re
import shlex

import click
import requests
import yaml

import nf_core.utils

# Set up local caching for requests to speed up remote queries
nf_core.utils.setup_requests_cachedir()

# Don't pick up debug logs from the requests package
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def run_linting(pipeline_dir, release_mode=False):
    """Runs all nf-core linting checks on a given Nextflow pipeline project
    in either `release` mode or `normal` mode (default). Returns an object
    of type :class:`PipelineLint` after finished.

    Args:
        pipeline_dir (str): The path to the Nextflow pipeline root directory
        release_mode (bool): Set this to `True`, if the linting should be run in the `release` mode.
                             See :class:`PipelineLint` for more information.

    Returns:
        An object of type :class:`PipelineLint` that contains all the linting results.
    """

    # Create the lint object
    lint_obj = PipelineLint(pipeline_dir)

    # Run the linting tests
    try:
        lint_obj.lint_pipeline(release_mode)
    except AssertionError as e:
        logging.critical("Critical error: {}".format(e))
        logging.info("Stopping tests...")
        lint_obj.print_results()
        return lint_obj

    # Print the results
    lint_obj.print_results()

    # Exit code
    if len(lint_obj.failed) > 0:
        logging.error(
            "Sorry, some tests failed - exiting with a non-zero error code...{}\n\n"
            .format("\n\tReminder: Lint tests were run in --release mode." if release_mode else '')
        )

    return lint_obj


class PipelineLint(object):
    """Object to hold linting information and results.
    All objects attributes are set, after the :func:`PipelineLint.lint_pipeline` function was called.

    Args:
        path (str): The path to the nf-core pipeline directory.

    Attributes:
        conda_config (dict): The parsed conda configuration file content (`environment.yml`).
        conda_package_info (dict): The conda package(s) information, based on the API requests to Anaconda cloud.
        config (dict): The Nextflow pipeline configuration file content.
        dockerfile (list): A list of lines (str) from the parsed Dockerfile.
        failed (list): A list of tuples of the form: `(<error no>, <reason>)`
        files (list): A list of files found during the linting process.
        minNextflowVersion (str): The minimum required Nextflow version to run the pipeline.
        passed (list): A list of tuples of the form: `(<passed no>, <reason>)`
        path (str): Path to the pipeline directory.
        pipeline_name (str): The pipeline name, without the `nf-core` tag, for example `hlatyping`.
        release_mode (bool): `True`, if you the to linting was run in release mode, `False` else.
        warned (list): A list of tuples of the form: `(<warned no>, <reason>)`

    **Attribute specifications**

    Some of the more complex attributes of a PipelineLint object.

    * `conda_config`::

        # Example
         {
            'name': 'nf-core-hlatyping',
            'channels': ['bioconda', 'conda-forge'],
            'dependencies': ['optitype=1.3.2', 'yara=0.9.6']
         }

    * `conda_package_info`::

        # See https://api.anaconda.org/package/bioconda/bioconda-utils as an example.
         {
            <package>: <API JSON repsonse object>
         }

    * `config`: Produced by calling Nextflow with :code:`nextflow config -flat <workflow dir>`. Here is an example from
        the `nf-core/hlatyping <https://github.com/nf-core/hlatyping>`_ pipeline::

            process.container = 'nfcore/hlatyping:1.1.1'
            params.help = false
            params.outdir = './results'
            params.bam = false
            params.single_end = false
            params.seqtype = 'dna'
            params.solver = 'glpk'
            params.igenomes_base = './iGenomes'
            params.clusterOptions = false
            ...
    """
    def __init__(self, path):
        """ Initialise linting object """
        self.release_mode = False
        self.path = path
        self.files = []
        self.config = {}
        self.pipeline_name = None
        self.minNextflowVersion = None
        self.dockerfile = []
        self.conda_config = {}
        self.conda_package_info = {}
        self.passed = []
        self.warned = []
        self.failed = []

    def lint_pipeline(self, release_mode=False):
        """Main linting function.

        Takes the pipeline directory as the primary input and iterates through
        the different linting checks in order. Collects any warnings or errors
        and returns summary at completion. Raises an exception if there is a
        critical error that makes the rest of the tests pointless (eg. no
        pipeline script). Results from this function are printed by the main script.

        Args:
            release_mode (boolean): Activates the release mode, which checks for
                consistent version tags of containers. Default is `False`.

        Returns:
            dict: Summary of test result messages structured as follows::

            {
                'pass': [
                    ( test-id (int), message (string) ),
                    ( test-id (int), message (string) )
                ],
                'warn': [(id, msg)],
                'fail': [(id, msg)],
            }

        Raises:
            If a critical problem is found, an ``AssertionError`` is raised.
        """
        check_functions = [
            'check_files_exist',
            'check_licence',
            'check_docker',
            'check_nextflow_config',
            'check_actions_branch_protection',
            'check_actions_ci',
            'check_actions_lint',
            'check_readme',
            'check_conda_env_yaml',
            'check_conda_dockerfile',
            'check_pipeline_todos',
            'check_pipeline_name'
        ]
        if release_mode:
            self.release_mode = True
            check_functions.extend([
                'check_version_consistency'
            ])
        with click.progressbar(check_functions, label='Running pipeline tests', item_show_func=repr) as fun_names:
            for fun_name in fun_names:
                getattr(self, fun_name)()
                if len(self.failed) > 0:
                    logging.error("Found test failures in '{}', halting lint run.".format(fun_name))
                    break

    def check_files_exist(self):
        """Checks a given pipeline directory for required files.

        Iterates through the pipeline's directory content and checkmarks files
        for presence.
        Files that **must** be present::

            'nextflow.config',
            'Dockerfile',
            ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
            'README.md',
            'CHANGELOG.md',
            'docs/README.md',
            'docs/output.md',
            'docs/usage.md'

        Files that *should* be present::

            'main.nf',
            'environment.yml',
            'conf/base.config',
            '.github/workflows/branch.yml',
            '.github/workflows/ci.yml',
            '.github/workfows/linting.yml'

        Files that *must not* be present::

            'Singularity'

        Files that *should not* be present::

            '.travis.yml'

        Raises:
            An AssertionError if neither `nextflow.config` or `main.nf` found.
        """

        # NB: Should all be files, not directories
        # List of lists. Passes if any of the files in the sublist are found.
        files_fail = [
            ['nextflow.config'],
            ['Dockerfile'],
            ['LICENSE', 'LICENSE.md', 'LICENCE', 'LICENCE.md'], # NB: British / American spelling
            ['README.md'],
            ['CHANGELOG.md'],
            [os.path.join('docs','README.md')],
            [os.path.join('docs','output.md')],
            [os.path.join('docs','usage.md')],
            [os.path.join('.github', 'workflows', 'branch.yml')],
            [os.path.join('.github', 'workflows','ci.yml')],
            [os.path.join('.github', 'workflows', 'linting.yml')]
        ]
        files_warn = [
            ['main.nf'],
            ['environment.yml'],
            [os.path.join('conf','base.config')]
        ]

        # List of strings. Dails / warns if any of the strings exist.
        files_fail_ifexists = [
            'Singularity'
        ]
        files_warn_ifexists = [
            '.travis.yml'
        ]

        def pf(file_path):
            return os.path.join(self.path, file_path)

        # First - critical files. Check that this is actually a Nextflow pipeline
        if not os.path.isfile(pf('nextflow.config')) and not os.path.isfile(pf('main.nf')):
            raise AssertionError('Neither nextflow.config or main.nf found! Is this a Nextflow pipeline?')

        # Files that cause an error if they don't exist
        for files in files_fail:
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(self._bold_list_items(files))))
                self.files.extend(files)
            else:
                self.failed.append((1, "File not found: {}".format(self._bold_list_items(files))))

        # Files that cause a warning if they don't exist
        for files in files_warn:
            if any([os.path.isfile(pf(f)) for f in files]):
                self.passed.append((1, "File found: {}".format(self._bold_list_items(files))))
                self.files.extend(files)
            else:
                self.warned.append((1, "File not found: {}".format(self._bold_list_items(files))))

        # Files that cause an error if they exist
        for file in files_fail_ifexists:
            if os.path.isfile(pf(file)):
                self.failed.append((1, "File must be removed: {}".format(self._bold_list_items(file))))
            else:
                self.passed.append((1, "File not found check: {}".format(self._bold_list_items(file))))

        # Files that cause a warning if they exist
        for file in files_warn_ifexists:
            if os.path.isfile(pf(file)):
                self.warned.append((1, "File should be removed: {}".format(self._bold_list_items(file))))
            else:
                self.passed.append((1, "File not found check: {}".format(self._bold_list_items(file))))

        # Load and parse files for later
        if 'environment.yml' in self.files:
            with open(os.path.join(self.path, 'environment.yml'), 'r') as fh:
                self.conda_config = yaml.safe_load(fh)

    def check_docker(self):
        """Checks that Dockerfile contains the string ``FROM``."""
        fn = os.path.join(self.path, "Dockerfile")
        content = ""
        with open(fn, 'r') as fh: content = fh.read()

        # Implicitly also checks if empty.
        if 'FROM ' in content:
            self.passed.append((2, "Dockerfile check passed"))
            self.dockerfile = [line.strip() for line in content.splitlines()]
            return

        self.failed.append((2, "Dockerfile check failed"))

    def check_licence(self):
        """Checks licence file is MIT.

        Currently the checkpoints are:
            * licence file must be long enough (4 or more lines)
            * licence contains the string *without restriction*
            * licence doesn't have any placeholder variables
        """
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
                placeholders = {'[year]', '[fullname]', '<YEAR>', '<COPYRIGHT HOLDER>', '<year>', '<copyright holders>'}
                if any([ph in content for ph in placeholders]):
                    self.failed.append((3, "Licence file contains placeholders: {}".format(fn)))
                    return

                self.passed.append((3, "Licence check passed"))
                return

        self.failed.append((3, "Couldn't find MIT licence file"))

    def check_nextflow_config(self):
        """Checks a given pipeline for required config variables.

        At least one string in each list must be present for fail and warn.
        Any config in config_fail_ifdefined results in a failure.

        Uses ``nextflow config -flat`` to parse pipeline ``nextflow.config``
        and print all config variables.
        NB: Does NOT parse contents of main.nf / nextflow script
        """

        # Fail tests if these are missing
        config_fail = [
            ['manifest.name'],
            ['manifest.nextflowVersion'],
            ['manifest.description'],
            ['manifest.version'],
            ['manifest.homePage'],
            ['timeline.enabled'],
            ['trace.enabled'],
            ['report.enabled'],
            ['dag.enabled'],
            ['process.cpus'],
            ['process.memory'],
            ['process.time'],
            ['params.outdir']
        ]
        # Throw a warning if these are missing
        config_warn = [
            ['manifest.mainScript'],
            ['timeline.file'],
            ['trace.file'],
            ['report.file'],
            ['dag.file'],
            ['params.reads','params.input','params.design'],
            ['process.container'],
            ['params.single_end']
        ]
        # Old depreciated vars - fail if present
        config_fail_ifdefined = [
            'params.version',
            'params.nf_required_version',
            'params.container',
            'params.singleEnd',
            'params.igenomesIgnore'
        ]

        # Get the nextflow config for this pipeline
        self.config = nf_core.utils.fetch_wf_config(self.path)
        for cfs in config_fail:
            for cf in cfs:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(self._bold_list_items(cf))))
                    break
            else:
                self.failed.append((4, "Config variable not found: {}".format(self._bold_list_items(cfs))))
        for cfs in config_warn:
            for cf in cfs:
                if cf in self.config.keys():
                    self.passed.append((4, "Config variable found: {}".format(self._bold_list_items(cf))))
                    break
            else:
                self.warned.append((4, "Config variable not found: {}".format(self._bold_list_items(cfs))))
        for cf in config_fail_ifdefined:
            if cf not in self.config.keys():
                self.passed.append((4, "Config variable (correctly) not found: {}".format(self._bold_list_items(cf))))
            else:
                self.failed.append((4, "Config variable (incorrectly) found: {}".format(self._bold_list_items(cf))))

        # Check and warn if the process configuration is done with deprecated syntax
        process_with_deprecated_syntax = list(set([re.search('^(process\.\$.*?)\.+.*$', ck).group(1) for ck in self.config.keys() if re.match(r'^(process\.\$.*?)\.+.*$', ck)]))
        for pd in process_with_deprecated_syntax:
            self.warned.append((4, "Process configuration is done with deprecated_syntax: {}".format(pd)))

        # Check the variables that should be set to 'true'
        for k in ['timeline.enabled', 'report.enabled', 'trace.enabled', 'dag.enabled']:
            if self.config.get(k) == 'true':
                self.passed.append((4, "Config variable '{}' had correct value: {}".format(k, self.config.get(k))))
            else:
                self.failed.append((4, "Config variable '{}' did not have correct value: {}".format(k, self.config.get(k))))

        # Check that the pipeline name starts with nf-core
        try:
            assert self.config.get('manifest.name', '').strip('\'"').startswith('nf-core/')
        except (AssertionError, IndexError):
            self.failed.append((4, "Config variable 'manifest.name' did not begin with nf-core/:\n    {}".format(self.config.get('manifest.name', '').strip('\'"'))))
        else:
            self.passed.append((4, "Config variable 'manifest.name' began with 'nf-core/'"))
            self.pipeline_name = self.config.get('manifest.name', '').strip("'").replace('nf-core/', '')

        # Check that the homePage is set to the GitHub URL
        try:
            assert self.config.get('manifest.homePage', '').strip('\'"').startswith('https://github.com/nf-core/')
        except (AssertionError, IndexError):
            self.failed.append((4, "Config variable 'manifest.homePage' did not begin with https://github.com/nf-core/:\n    {}".format(self.config.get('manifest.homePage', '').strip('\'"'))))
        else:
            self.passed.append((4, "Config variable 'manifest.homePage' began with 'https://github.com/nf-core/'"))

        # Check that the DAG filename ends in `.svg`
        if 'dag.file' in self.config:
            if self.config['dag.file'].strip('\'"').endswith('.svg'):
                self.passed.append((4, "Config variable 'dag.file' ended with .svg"))
            else:
                self.failed.append((4, "Config variable 'dag.file' did not end with .svg"))

        # Check that the minimum nextflowVersion is set properly
        if 'manifest.nextflowVersion' in self.config:
            if self.config.get('manifest.nextflowVersion', '').strip('"\'').lstrip('!').startswith('>='):
                self.passed.append((4, "Config variable 'manifest.nextflowVersion' started with >= or !>="))
                # Save self.minNextflowVersion for convenience
                nextflowVersionMatch = re.search(r'[0-9\.]+(-edge)?', self.config.get('manifest.nextflowVersion', ''))
                if nextflowVersionMatch:
                    self.minNextflowVersion = nextflowVersionMatch.group(0)
                else:
                    self.minNextflowVersion = None
            else:
                self.failed.append((4, "Config variable 'manifest.nextflowVersion' did not start with '>=' or '!>=' : '{}'".format(self.config.get('manifest.nextflowVersion', '')).strip('"\'')))

        # Check that the process.container name is pulling the version tag or :dev
        if self.config.get('process.container'):
            container_name = '{}:{}'.format(self.config.get('manifest.name').replace('nf-core','nfcore').strip("'"), self.config.get('manifest.version', '').strip("'"))
            if 'dev' in self.config.get('manifest.version', '') or not self.config.get('manifest.version'):
                container_name = '{}:dev'.format(self.config.get('manifest.name').replace('nf-core','nfcore').strip("'"))
            try:
                assert self.config.get('process.container', '').strip("'") == container_name
            except AssertionError:
                if self.release_mode:
                    self.failed.append((4, "Config variable process.container looks wrong. Should be '{}' but is '{}'".format(container_name, self.config.get('process.container', '').strip("'"))))
                else:
                    self.warned.append((4, "Config variable process.container looks wrong. Should be '{}' but is '{}'. Fix this before you make a release of your pipeline!".format(container_name, self.config.get('process.container', '').strip("'"))))
            else:
                self.passed.append((4, "Config variable process.container looks correct: '{}'".format(container_name)))

        # Check that the pipeline version contains `dev`
        if not self.release_mode and 'manifest.version' in self.config:
            if self.config['manifest.version'].strip(' \'"').endswith('dev'):
                self.passed.append((4, "Config variable manifest.version ends in 'dev': '{}'".format(self.config['manifest.version'])))
            else:
                self.warned.append((4, "Config variable manifest.version should end in 'dev': '{}'".format(self.config['manifest.version'])))
        elif 'manifest.version' in self.config:
            if 'dev' in self.config['manifest.version']:
                self.failed.append((4, "Config variable manifest.version should not contain 'dev' for a release: '{}'".format(self.config['manifest.version'])))
            else:
                self.passed.append((4, "Config variable manifest.version does not contain 'dev' for release: '{}'".format(self.config['manifest.version'])))

    def check_actions_branch_protection(self):
        """Checks that the GitHub Actions branch protection workflow is valid.

        Makes sure PRs can only come from nf-core dev or 'patch' of a fork.
        """
        fn = os.path.join(self.path, '.github', 'workflows', 'branch.yml')
        if os.path.isfile(fn):
            with open(fn, 'r') as fh:
                branchwf = yaml.safe_load(fh)

            # Check that the action is turned on for PRs to master
            try:
                assert('master' in branchwf[True]['pull_request']['branches'])
            except (AssertionError, KeyError):
                self.failed.append((5, "GitHub Actions 'branch' workflow should be triggered for PRs to master: '{}'".format(fn)))
            else:
                self.passed.append((5, "GitHub Actions 'branch' workflow is triggered for PRs to master: '{}'".format(fn)))

            # Check that PRs are only ok if coming from an nf-core `dev` branch or a fork `patch` branch
            PRMasterCheck = "{{ [[ $(git remote get-url origin) == *nf-core/{} ]] && [[ ${{GITHUB_HEAD_REF}} = \"dev\" ]]; }} || [[ ${{GITHUB_HEAD_REF}} == \"patch\" ]]".format(self.pipeline_name.lower())
            steps = branchwf['jobs']['test']['steps']
            try:
                steps = branchwf['jobs']['test']['steps']
                assert(any([PRMasterCheck in step.get('run', []) for step in steps]))
            except (AssertionError, KeyError):
                self.failed.append((5, "GitHub Actions 'branch' workflow should check that forks don't submit PRs to master: '{}'".format(fn)))
            else:
                self.passed.append((5, "GitHub Actions 'branch' workflow checks that forks don't submit PRs to master: '{}'".format(fn)))

    def check_actions_ci(self):
        """Checks that the GitHub Actions CI workflow is valid

        Makes sure tests run with the required nextflow version.
        """
        fn = os.path.join(self.path, '.github', 'workflows', 'ci.yml')
        if os.path.isfile(fn):
            with open(fn, 'r') as fh:
                ciwf = yaml.safe_load(fh)

            # Check that the action is turned on for push and pull requests
            try:
                assert('push' in ciwf[True])
                assert('pull_request' in ciwf[True])
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "GitHub Actions CI workflow must be triggered on PR and push: '{}'".format(fn)))
            else:
                self.passed.append((5, "GitHub Actions CI workflow is triggered on PR and push: '{}'".format(fn)))

            # Check that we're pulling the right docker image and tagging it properly
            if self.config.get('process.container', ''):
                docker_notag = re.sub(r':(?:[\.\d]+|dev)$', '', self.config.get('process.container', '').strip('"\''))
                docker_withtag = self.config.get('process.container', '').strip('"\'')
                docker_pull_cmd = 'docker pull {}:dev'.format(docker_notag)
                try:
                    steps = ciwf['jobs']['test']['steps']
                    assert(any([docker_pull_cmd in step['run'] for step in steps if 'run' in step.keys()]))
                except (AssertionError, KeyError, TypeError):
                    self.failed.append((5, "CI is not pulling the correct docker image. Should be:\n    '{}'".format(docker_pull_cmd)))
                else:
                    self.passed.append((5, "CI is pulling the correct docker image: {}".format(docker_pull_cmd)))

                docker_tag_cmd = 'docker tag {}:dev {}'.format(docker_notag, docker_withtag)
                try:
                    steps = ciwf['jobs']['test']['steps']
                    assert(any([docker_tag_cmd in step['run'] for step in steps if 'run' in step.keys()]))
                except (AssertionError, KeyError, TypeError):
                    self.failed.append((5, "CI is not tagging docker image correctly. Should be:\n    '{}'".format(docker_tag_cmd)))
                else:
                    self.passed.append((5, "CI is tagging docker image correctly: {}".format(docker_tag_cmd)))

            # Check that we are testing the minimum nextflow version
            try:
                matrix = ciwf['jobs']['test']['strategy']['matrix']['nxf_ver']
                assert(any([self.minNextflowVersion in matrix]))
            except (KeyError, TypeError):
                self.failed.append((5, "Continuous integration does not check minimum NF version: '{}'".format(fn)))
            except AssertionError:
                self.failed.append((5, "Minimum NF version differed from CI and what was set in the pipelines manifest: {}".format(fn)))
            else:
                self.passed.append((5, "Continuous integration checks minimum NF version: '{}'".format(fn)))

    def check_actions_lint(self):
        """Checks that the GitHub Actions lint workflow is valid

        Makes sure ``nf-core lint`` and ``markdownlint`` runs.
        """
        fn = os.path.join(self.path, '.github', 'workflows', 'linting.yml')
        if os.path.isfile(fn):
            with open(fn, 'r') as fh:
                lintwf = yaml.safe_load(fh)

            # Check that the action is turned on for push and pull requests
            try:
                assert('push' in lintwf[True])
                assert('pull_request' in lintwf[True])
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "GitHub Actions linting workflow must be triggered on PR and push: '{}'".format(fn)))
            else:
                self.passed.append((5, "GitHub Actions linting workflow is triggered on PR and push: '{}'".format(fn)))

            # Check that the Markdown linting runs
            Markdownlint_cmd = 'markdownlint ${GITHUB_WORKSPACE} -c ${GITHUB_WORKSPACE}/.github/markdownlint.yml'
            try:
                steps = lintwf['jobs']['Markdown']['steps']
                assert(any([Markdownlint_cmd in step['run'] for step in steps if 'run' in step.keys()]))
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "Continuous integration must run Markdown lint Tests: '{}'".format(fn)))
            else:
                self.passed.append((5, "Continuous integration runs Markdown lint Tests: '{}'".format(fn)))


            # Check that the nf-core linting runs
            nfcore_lint_cmd = 'nf-core lint ${GITHUB_WORKSPACE}'
            try:
                steps = lintwf['jobs']['nf-core']['steps']
                assert(any([ nfcore_lint_cmd in step['run'] for step in steps if 'run' in step.keys()]))
            except (AssertionError, KeyError, TypeError):
                self.failed.append((5, "Continuous integration must run nf-core lint Tests: '{}'".format(fn)))
            else:
                self.passed.append((5, "Continuous integration runs nf-core lint Tests: '{}'".format(fn)))

    def check_readme(self):
        """Checks the repository README file for errors.

        Currently just checks the badges at the top of the README.
        """
        with open(os.path.join(self.path, 'README.md'), 'r') as fh:
            content = fh.read()

        # Check that there is a readme badge showing the minimum required version of Nextflow
        # and that it has the correct version
        nf_badge_re = r"\[!\[Nextflow\]\(https://img\.shields\.io/badge/nextflow-%E2%89%A5([\d\.]+)-brightgreen\.svg\)\]\(https://www\.nextflow\.io/\)"
        match = re.search(nf_badge_re, content)
        if match:
            nf_badge_version = match.group(1).strip('\'"')
            try:
                assert nf_badge_version == self.minNextflowVersion
            except (AssertionError, KeyError):
                self.failed.append((6, "README Nextflow minimum version badge does not match config. Badge: '{}', Config: '{}'".format(nf_badge_version, self.minNextflowVersion)))
            else:
                self.passed.append((6, "README Nextflow minimum version badge matched config. Badge: '{}', Config: '{}'".format(nf_badge_version, self.minNextflowVersion)))
        else:
            self.warned.append((6, "README did not have a Nextflow minimum version badge."))

        # Check that we have a bioconda badge if we have a bioconda environment file
        if 'environment.yml' in self.files:
            bioconda_badge = '[![install with bioconda](https://img.shields.io/badge/install%20with-bioconda-brightgreen.svg)](http://bioconda.github.io/)'
            if bioconda_badge in content:
                self.passed.append((6, "README had a bioconda badge"))
            else:
                self.failed.append((6, "Found a bioconda environment.yml file but no badge in the README"))


    def check_version_consistency(self):
        """Checks container tags versions.

        Runs on ``process.container`` (if set) and ``$GITHUB_REF`` (if a GitHub Actions release).

        Checks that:
            * the container has a tag
            * the version numbers are numeric
            * the version numbers are the same as one-another
        """
        versions = {}
        # Get the version definitions
        # Get version from nextflow.config
        versions['manifest.version'] = self.config.get('manifest.version', '').strip(' \'"')

        # Get version from the docker slug
        if self.config.get('process.container', '') and \
                not ':' in self.config.get('process.container', ''):
            self.failed.append((7, "Docker slug seems not to have "
                "a version tag: {}".format(self.config.get('process.container', ''))))
            return

        # Get config container slugs, (if set; one container per workflow)
        if self.config.get('process.container', ''):
            versions['process.container'] = self.config.get('process.container', '').strip(' \'"').split(':')[-1]
        if self.config.get('process.container', ''):
            versions['process.container'] = self.config.get('process.container', '').strip(' \'"').split(':')[-1]

        # Get version from the GITHUB_REF env var if this is a release
        if os.environ.get('GITHUB_REF', '').startswith('refs/tags/') and os.environ.get('GITHUB_REPOSITORY', '') != 'nf-core/tools':
            versions['GITHUB_REF'] = os.path.basename(os.environ['GITHUB_REF'].strip(' \'"'))

        # Check if they are all numeric
        for v_type, version in versions.items():
            if not version.replace('.', '').isdigit():
                self.failed.append((7, "{} was not numeric: {}!".format(v_type, version)))
                return

        # Check if they are consistent
        if len(set(versions.values())) != 1:
            self.failed.append((7, "The versioning is not consistent between container, release tag "
                "and config. Found {}".format(
                    ", ".join(["{} = {}".format(k, v) for k,v in versions.items()])
                )))
            return

        self.passed.append((7, "Version tags are numeric and consistent between container, release tag and config."))

    def check_conda_env_yaml(self):
        """Checks that the conda environment file is valid.

        Checks that:
            * a name is given and is consistent with the pipeline name
            * check that dependency versions are pinned
            * dependency versions are the latest available
        """
        if 'environment.yml' not in self.files:
            return

        # Check that the environment name matches the pipeline name
        pipeline_version = self.config.get('manifest.version', '').strip(' \'"')
        expected_env_name = 'nf-core-{}-{}'.format(self.pipeline_name.lower(), pipeline_version)
        if self.conda_config['name'] != expected_env_name:
            self.failed.append((8, "Conda environment name is incorrect ({}, should be {})".format(self.conda_config['name'], expected_env_name)))
        else:
            self.passed.append((8, "Conda environment name was correct ({})".format(expected_env_name)))

        # Check conda dependency list
        for dep in self.conda_config.get('dependencies', []):
            if isinstance(dep, str):
                # Check that each dependency has a version number
                try:
                    assert dep.count('=') == 1
                except AssertionError:
                    self.failed.append((8, "Conda dependency did not have pinned version number: {}".format(dep)))
                else:
                    self.passed.append((8, "Conda dependency had pinned version number: {}".format(dep)))

                    try:
                        depname, depver = dep.split('=', 1)
                        self.check_anaconda_package(dep)
                    except ValueError:
                        pass
                    else:
                        # Check that required version is available at all
                        if depver not in self.conda_package_info[dep].get('versions'):
                            self.failed.append((8, "Conda dependency had an unknown version: {}".format(dep)))
                            continue  # No need to test for latest version, continue linting
                        # Check version is latest available
                        last_ver = self.conda_package_info[dep].get('latest_version')
                        if last_ver is not None and last_ver != depver:
                            self.warned.append((8, "Conda package is not latest available: {}, {} available".format(dep, last_ver)))
                        else:
                            self.passed.append((8, "Conda package is latest available: {}".format(dep)))

            elif isinstance(dep, dict):
                for pip_dep in dep.get('pip', []):
                    # Check that each pip dependency has a version number
                    try:
                        assert pip_dep.count('=') == 2
                    except AssertionError:
                        self.failed.append((8, "Pip dependency did not have pinned version number: {}".format(pip_dep)))
                    else:
                        self.passed.append((8, "Pip dependency had pinned version number: {}".format(pip_dep)))

                        try:
                            pip_depname, pip_depver = pip_dep.split('==', 1)
                            self.check_pip_package(pip_dep)
                        except ValueError:
                            pass
                        else:
                            # Check, if PyPi package version is available at all
                            if pip_depver not in self.conda_package_info[pip_dep].get('releases').keys():
                                self.failed.append((8, "PyPi package had an unknown version: {}".format(pip_depver)))
                                continue  # No need to test latest version, if not available
                            last_ver = self.conda_package_info[pip_dep].get('info').get('version')
                            if last_ver is not None and last_ver != pip_depver:
                                self.warned.append((8, "PyPi package is not latest available: {}, {} available".format(pip_depver, last_ver)))
                            else:
                                self.passed.append((8, "PyPi package is latest available: {}".format(pip_depver)))

    def check_anaconda_package(self, dep):
        """Query conda package information.

        Sends a HTTP GET request to the Anaconda remote API.

        Args:
            dep (str): A conda package name.

        Raises:
            A ValueError, if the package name can not be resolved.
        """
        # Check if each dependency is the latest available version
        depname, depver = dep.split('=', 1)
        dep_channels = self.conda_config.get('channels', [])
        # 'defaults' isn't actually a channel name. See https://docs.anaconda.com/anaconda/user-guide/tasks/using-repositories/
        if 'defaults' in dep_channels:
            dep_channels.remove('defaults')
            dep_channels.extend([
                'main',
                'anaconda',
                'r',
                'free',
                'archive',
                'anaconda-extras'
            ])
        if '::' in depname:
            dep_channels = [depname.split('::')[0]]
            depname = depname.split('::')[1]
        for ch in dep_channels:
            anaconda_api_url = 'https://api.anaconda.org/package/{}/{}'.format(ch, depname)
            try:
                response = requests.get(anaconda_api_url, timeout=10)
            except (requests.exceptions.Timeout):
                self.warned.append((8, "Anaconda API timed out: {}".format(anaconda_api_url)))
                raise ValueError
            except (requests.exceptions.ConnectionError):
                self.warned.append((8, "Could not connect to Anaconda API"))
                raise ValueError
            else:
                if response.status_code == 200:
                    dep_json = response.json()
                    self.conda_package_info[dep] = dep_json
                    return
                elif response.status_code != 404:
                    self.warned.append((8, "Anaconda API returned unexpected response code '{}' for: {}\n{}".format(response.status_code, anaconda_api_url, response)))
                    raise ValueError
                elif response.status_code == 404:
                    logging.debug("Could not find {} in conda channel {}".format(dep, ch))
        else:
            # We have looped through each channel and had a 404 response code on everything
            self.failed.append((8, "Could not find Conda dependency using the Anaconda API: {}".format(dep)))
            raise ValueError

    def check_pip_package(self, dep):
        """Query PyPi package information.

        Sends a HTTP GET request to the PyPi remote API.

        Args:
            dep (str): A PyPi package name.

        Raises:
            A ValueError, if the package name can not be resolved or the connection timed out.
        """
        pip_depname, pip_depver = dep.split('=', 1)
        pip_api_url = 'https://pypi.python.org/pypi/{}/json'.format(pip_depname)
        try:
            response = requests.get(pip_api_url, timeout=10)
        except (requests.exceptions.Timeout):
            self.warned.append((8, "PyPi API timed out: {}".format(pip_api_url)))
            raise ValueError
        except (requests.exceptions.ConnectionError):
            self.warned.append((8, "PyPi API Connection error: {}".format(pip_api_url)))
            raise ValueError
        else:
            if response.status_code == 200:
                pip_dep_json = response.json()
                self.conda_package_info[dep] = pip_dep_json
            else:
                self.failed.append((8, "Could not find pip dependency using the PyPi API: {}".format(dep)))
                raise ValueError

    def check_conda_dockerfile(self):
        """Checks the Docker build file.

        Checks that:
            * a name is given and is consistent with the pipeline name
            * dependency versions are pinned
            * dependency versions are the latest available
        """
        if 'environment.yml' not in self.files or len(self.dockerfile) == 0:
            return

        expected_strings = [
            "FROM nfcore/base:{}".format('dev' if 'dev' in nf_core.__version__ else nf_core.__version__),
            'COPY environment.yml /',
            'RUN conda env create -f /environment.yml && conda clean -a',
            'RUN conda env export --name {} > {}.yml'.format(self.conda_config['name'], self.conda_config['name']),
            'ENV PATH /opt/conda/envs/{}/bin:$PATH'.format(self.conda_config['name'])
        ]

        difference = set(expected_strings) - set(self.dockerfile)
        if not difference:
            self.passed.append((9, "Found all expected strings in Dockerfile file"))
        else:
            for missing in difference:
                self.failed.append((9, "Could not find Dockerfile file string: {}".format(missing)))

    def check_pipeline_todos(self):
        """ Go through all template files looking for the string 'TODO nf-core:' """
        ignore = ['.git']
        if os.path.isfile(os.path.join(self.path, '.gitignore')):
            with io.open(os.path.join(self.path, '.gitignore'), 'rt', encoding='latin1') as fh:
                for l in fh:
                    ignore.append(os.path.basename(l.strip().rstrip('/')))
        for root, dirs, files in os.walk(self.path):
            # Ignore files
            for i in ignore:
                if i in dirs:
                    dirs.remove(i)
                if i in files:
                    files.remove(i)
            for fname in files:
                with io.open(os.path.join(root, fname), 'rt', encoding='latin1') as fh:
                    for l in fh:
                        if 'TODO nf-core' in l:
                            l = l.replace('<!--', '').replace('-->', '').replace('# TODO nf-core: ', '').replace('// TODO nf-core: ', '').replace('TODO nf-core: ', '').strip()
                            if len(fname) + len(l) > 50:
                                l = '{}..'.format(l[:50-len(fname)])
                            self.warned.append((10, "TODO string found in '{}': {}".format(fname,l)))

    def check_pipeline_name(self):
        """Check whether pipeline name adheres to lower case/no hyphen naming convention"""

        if self.pipeline_name.islower() and self.pipeline_name.isalpha():
            self.passed.append((12, "Name adheres to nf-core convention"))
        if not self.pipeline_name.islower():
            self.warned.append((12, "Naming does not adhere to nf-core conventions: Contains uppercase letters"))
        if not self.pipeline_name.isalpha():
            self.warned.append((12, "Naming does not adhere to nf-core conventions: Contains non alphabetical characters"))



    def print_results(self):
        # Print results
        rl = "\n  Using --release mode linting tests" if self.release_mode else ''
        logging.info("{}\n          LINTING RESULTS\n{}\n".format(click.style('='*29, dim=True), click.style('='*35, dim=True)) +
            click.style("  [{}] {:>4} tests passed\n".format(u'\u2714', len(self.passed)), fg='green') +
            click.style("  [!] {:>4} tests had warnings\n".format(len(self.warned)), fg='yellow') +
            click.style("  [{}] {:>4} tests failed".format(u'\u2717', len(self.failed)), fg='red') + rl
        )

        # Helper function to format test links nicely
        def format_result(test_results):
            """
            Given an error message ID and the message text, return a nicely formatted
            string for the terminal with appropriate ASCII colours.
            """
            print_results = []
            for eid, msg in test_results:
                url = click.style("http://nf-co.re/errors#{}".format(eid), fg='blue')
                print_results.append('{} : {}'.format(url, msg))
            return "\n  ".join(print_results)

        if len(self.passed) > 0:
            logging.debug("{}\n  {}".format(click.style("Test Passed:", fg='green'), format_result(self.passed)))
        if len(self.warned) > 0:
            logging.warning("{}\n  {}".format(click.style("Test Warnings:", fg='yellow'), format_result(self.warned)))
        if len(self.failed) > 0:
            logging.error("{}\n  {}".format(click.style("Test Failures:", fg='red'), format_result(self.failed)))


    def _bold_list_items(self, files):
        if not isinstance(files, list):
            files = [files]
        bfiles = [click.style(f, bold=True) for f in files]
        return ' or '.join(bfiles)
