#!/usr/bin/env python
"""Some tests covering the linting code.
Provide example wokflow directory contents like:

    --tests
        |--lint_examples
        |     |--missing_license
        |     |     |...<files here>
        |     |--missing_config
        |     |     |....<files here>
        |     |...
        |--test_lint.py
"""
import os
import yaml
import requests
import pytest
import unittest
import mock
import nf_core.lint


def listfiles(path):
    files_found = []
    for (_,_,files) in os.walk(path):
        files_found.extend(files)
    return files_found

def pf(wd, path):
    return os.path.join(wd, path)

WD = os.path.dirname(__file__)
PATH_CRITICAL_EXAMPLE =  pf(WD, 'lint_examples/critical_example')
PATH_FAILING_EXAMPLE = pf(WD, 'lint_examples/failing_example')
PATH_WORKING_EXAMPLE = pf(WD, 'lint_examples/minimal_working_example')
PATH_MISSING_LICENSE_EXAMPLE = pf(WD, 'lint_examples/missing_license_example')
PATHS_WRONG_LICENSE_EXAMPLE = [pf(WD, 'lint_examples/wrong_license_example'),
    pf(WD, 'lint_examples/license_incomplete_example')]

# The maximum sum of passed tests currently possible
MAX_PASS_CHECKS = 61
# The additional tests passed for releases
ADD_PASS_RELEASE = 1

class TestLint(unittest.TestCase):
    """Class for lint tests"""

    def assess_lint_status(self, lint_obj, **expected):
        """Little helper function for assessing the lint
        object status lists"""
        for list_type, expect in expected.items():
            observed = len(getattr(lint_obj, list_type))
            oberved_list = yaml.safe_dump(getattr(lint_obj, list_type))
            self.assertEqual(observed, expect, "Expected {} tests in '{}', but found {}.\n{}".format(expect, list_type.upper(), observed, oberved_list))

    def test_call_lint_pipeline_pass(self):
        """Test the main execution function of PipelineLint (pass)
        This should not result in any exception for the minimal
        working example"""
        lint_obj = nf_core.lint.run_linting(PATH_WORKING_EXAMPLE, False)
        expectations = {"failed": 0, "warned": 3, "passed": MAX_PASS_CHECKS}
        self.assess_lint_status(lint_obj, **expectations)

    @pytest.mark.xfail(raises=AssertionError)
    def test_call_lint_pipeline_fail(self):
        """Test the main execution function of PipelineLint (fail)
        This should fail after the first test and halt execution """
        lint_obj = nf_core.lint.run_linting(PATH_FAILING_EXAMPLE, False)
        expectations = {"failed": 4, "warned": 2, "passed": 7}
        self.assess_lint_status(lint_obj, **expectations)

    def test_call_lint_pipeline_release(self):
        """Test the main execution function of PipelineLint when running with --release"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.lint_pipeline(release_mode=True)
        expectations = {"failed": 0, "warned": 3, "passed": MAX_PASS_CHECKS + ADD_PASS_RELEASE}
        self.assess_lint_status(lint_obj, **expectations)

    def test_failing_dockerfile_example(self):
        """Tests for empty Dockerfile"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_docker()
        self.assess_lint_status(lint_obj, failed=1)

    @pytest.mark.xfail(raises=AssertionError)
    def test_critical_missingfiles_example(self):
        """Tests for missing nextflow config and main.nf files"""
        lint_obj = nf_core.lint.run_linting(PATH_CRITICAL_EXAMPLE, False)

    def test_failing_missingfiles_example(self):
        """Tests for missing files like Dockerfile or LICENSE"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_files_exist()
        expectations = {"failed": 5, "warned": 1, "passed": len(listfiles(PATH_WORKING_EXAMPLE)) - 5 - 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_mit_licence_example_pass(self):
        """Tests that MIT test works with good MIT licences"""
        good_lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
        good_lint_obj.check_licence()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(good_lint_obj, **expectations)

    def test_mit_license_example_with_failed(self):
        """Tests that MIT test works with bad MIT licences"""
        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        bad_lint_obj.check_licence()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(bad_lint_obj, **expectations)

    def test_config_variable_example_pass(self):
        """Tests that config variable existence test works with good pipeline example"""
        good_lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        good_lint_obj.check_nextflow_config()
        expectations = {"failed": 0, "warned": 0, "passed": 32}
        self.assess_lint_status(good_lint_obj, **expectations)

    def test_config_variable_example_with_failed(self):
        """Tests that config variable existence test fails with bad pipeline example"""
        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        bad_lint_obj.check_nextflow_config()
        expectations = {"failed": 18, "warned": 9, "passed": 6}
        self.assess_lint_status(bad_lint_obj, **expectations)

    @pytest.mark.xfail(raises=AssertionError)
    def test_config_variable_error(self):
        """Tests that config variable existence test falls over nicely with nextflow can't run"""
        bad_lint_obj = nf_core.lint.PipelineLint('/non/existant/path')
        bad_lint_obj.check_nextflow_config()

    def test_ci_conf_pass(self):
        """Tests that the continous integration config checks work with a good example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.minNextflowVersion = '0.32.0'
        lint_obj.check_ci_config()
        expectations = {"failed": 0, "warned": 0, "passed": 3}
        self.assess_lint_status(lint_obj, **expectations)

    def test_ci_conf_fail_wrong_nf_version(self):
        """Tests that the CI check fails with the wrong NXF version"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.minNextflowVersion = '0.28.0'
        lint_obj.check_ci_config()
        expectations = {"failed": 1, "warned": 0, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_ci_conf_fail(self):
        """Tests that the continous integration config checks work with a bad example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_ci_config()
        expectations = {"failed": 2, "warned": 0, "passed": 0}

    def test_wrong_license_examples_with_failed(self):
        """Tests for checking the license test behavior"""
        for example in PATHS_WRONG_LICENSE_EXAMPLE:
            lint_obj = nf_core.lint.PipelineLint(example)
            lint_obj.check_licence()
            expectations = {"failed": 1, "warned": 0, "passed": 0}
            self.assess_lint_status(lint_obj, **expectations)

    def test_missing_license_example(self):
        """Tests for missing license behavior"""
        lint_obj = nf_core.lint.PipelineLint(PATH_MISSING_LICENSE_EXAMPLE)
        lint_obj.check_licence()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_readme_pass(self):
        """Tests that the pipeline README file checks work with a good example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.minNextflowVersion = '0.32.0'
        lint_obj.files = ['environment.yml']
        lint_obj.check_readme()
        expectations = {"failed": 0, "warned": 0, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_readme_warn(self):
        """Tests that the pipeline README file checks fail  """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.minNextflowVersion = '0.28.0'
        lint_obj.check_readme()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_readme_fail(self):
        """Tests that the pipeline README file checks give warnings with a bad example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.check_readme()
        expectations = {"failed": 1, "warned": 1, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_dockerfile_pass(self):
        """Tests if a valid Dockerfile passes the lint checks"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.check_docker()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_version_consistency_pass(self):
        """Tests the workflow version and container version sucessfully"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config["manifest.version"] = "0.4"
        lint_obj.config["params.container"] = "nfcore/tools:0.4"
        lint_obj.check_version_consistency()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_version_consistency_with_env_fail(self):
        """Tests the behaviour, when a git activity is a release
        and simulate wrong release tag"""
        os.environ["TRAVIS_TAG"] = "0.5"
        os.environ["TRAVIS_REPO_SLUG"] = "nf-core/testpipeline"
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config["manifest.version"] = "0.4"
        lint_obj.config["params.container"] = "nfcore/tools:0.4"
        lint_obj.config["process.container"] = "nfcore/tools:0.4"
        lint_obj.check_version_consistency()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_version_consistency_with_numeric_fail(self):
        """Tests the behaviour, when a git activity is a release
        and simulate wrong release tag"""
        os.environ["TRAVIS_TAG"] = "0.5dev"
        os.environ["TRAVIS_REPO_SLUG"] = "nf-core/testpipeline"
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config["manifest.version"] = "0.4"
        lint_obj.config["params.container"] = "nfcore/tools:0.4"
        lint_obj.check_version_consistency()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_version_consistency_with_no_docker_version_fail(self):
        """Tests the behaviour, when a git activity is a release
        and simulate wrong missing docker version tag"""
        os.environ["TRAVIS_TAG"] = "0.4"
        os.environ["TRAVIS_REPO_SLUG"] = "nf-core/testpipeline"
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config["manifest.version"] = "0.4"
        lint_obj.config["params.container"] = "nfcore/tools"
        lint_obj.check_version_consistency()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_version_consistency_with_env_pass(self):
        """Tests the behaviour, when a git activity is a release
        and simulate correct release tag"""
        os.environ["TRAVIS_TAG"] = "0.4"
        os.environ["TRAVIS_REPO_SLUG"] = "nf-core/testpipeline"
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config["manifest.version"] = "0.4"
        lint_obj.config["params.container"] = "nfcore/tools:0.4"
        lint_obj.check_version_consistency()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_env_pass(self):
        """ Tests the conda environment config checks with a working example """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        with open(os.path.join(PATH_WORKING_EXAMPLE, 'environment.yml'), 'r') as fh:
            lint_obj.conda_config = yaml.load(fh)
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 0, "warned": 3, "passed": 4}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_env_fail(self):
        """ Tests the conda environment config fails with a bad example """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        with open(os.path.join(PATH_WORKING_EXAMPLE, 'environment.yml'), 'r') as fh:
            lint_obj.conda_config = yaml.load(fh)
        lint_obj.conda_config['dependencies'] = ['fastqc', 'multiqc=0.9', 'notapackaage=0.4']
        lint_obj.pipeline_name = 'not_tools'
        lint_obj.config['manifest.version'] = '0.23'
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 3, "warned": 1, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    @mock.patch('requests.get')
    @pytest.mark.xfail(raises=ValueError)
    def test_conda_env_timeout(self, mock_get):
        """ Tests the conda environment handles API timeouts """
        # Define the behaviour of the request get mock
        mock_get.side_effect = requests.exceptions.Timeout()
        # Now do the test
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.conda_config['channels'] = ['bioconda']
        lint_obj.check_anaconda_package('multiqc=1.6')

    def test_conda_env_skip(self):
        """ Tests the conda environment config is skipped when not needed """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 0, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_dockerfile_pass(self):
        """ Tests the conda Dockerfile test works with a working example """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        with open(os.path.join(PATH_WORKING_EXAMPLE, 'Dockerfile'), 'r') as fh:
            lint_obj.dockerfile = fh.read().splitlines()
        lint_obj.conda_config['name'] = 'nf-core-tools-0.4'
        lint_obj.check_conda_dockerfile()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_dockerfile_fail(self):
        """ Tests the conda Dockerfile test fails with a bad example """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.conda_config['name'] = 'nf-core-tools-0.4'
        lint_obj.dockerfile = ['fubar']
        lint_obj.check_conda_dockerfile()
        expectations = {"failed": 4, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_dockerfile_skip(self):
        """ Tests the conda Dockerfile test is skipped when not needed """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.check_conda_dockerfile()
        expectations = {"failed": 0, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_pip_no_version_fail(self):
        """ Tests the pip dependency version definition is present """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['multiqc']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 1, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_pip_package_not_latest_warn(self):
        """ Tests the pip dependency version definition is present """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['multiqc==1.4']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 0, "warned": 1, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    @mock.patch('requests.get')
    def test_pypi_timeout_warn(self, mock_get):
        """ Tests the PyPi connection and simulates a request timeout, which should
        return in an addiional warning in the linting """
        # Define the behaviour of the request get mock
        mock_get.side_effect = requests.exceptions.Timeout()
        # Now do the test
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['multiqc==1.5']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 0, "warned": 1, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    @mock.patch('requests.get')
    def test_pypi_connection_error_warn(self, mock_get):
        """ Tests the PyPi connection and simulates a connection error, which should
        result in an additional warning, as we cannot test if dependent module is latest """
        # Define the behaviour of the request get mock
        mock_get.side_effect = requests.exceptions.ConnectionError()
        # Now do the test
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['multiqc==1.5']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 0, "warned": 1, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_pip_dependency_fail(self):
        """ Tests the PyPi API package information query """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['notpresent==1.5']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 1, "warned": 0, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_conda_dependency_fails(self):
        """ Tests that linting fails, if conda dependency
        package version is not available on Anaconda.
        """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': ['openjdk=0.0.0']}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 1, "warned": 0, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)

    def test_pip_dependency_fails(self):
        """ Tests that linting fails, if conda dependency
        package version is not available on Anaconda.
        """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.files = ['environment.yml']
        lint_obj.pipeline_name = 'tools'
        lint_obj.config['manifest.version'] = '0.4'
        lint_obj.conda_config = {'name': 'nf-core-tools-0.4', 'dependencies': [{'pip': ['multiqc==0.0']}]}
        lint_obj.check_conda_env_yaml()
        expectations = {"failed": 1, "warned": 0, "passed": 2}
        self.assess_lint_status(lint_obj, **expectations)
