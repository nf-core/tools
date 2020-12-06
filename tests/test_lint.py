#!/usr/bin/env python
"""Some tests covering the linting code.
"""
import json
import mock
import os
import pytest
import requests
import shutil
import subprocess
import tempfile
import unittest
import yaml

import nf_core.create
import nf_core.lint


class TestLint(unittest.TestCase):
    """Class for lint tests"""

    def setUp(self):
        """Function that runs at start of tests for common resources

        Use nf_core.create() to make a pipeline that we can use for testing
        """
        self.test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
        create_obj = nf_core.create.PipelineCreate(
            "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=self.test_pipeline_dir
        )
        create_obj.init_pipeline()

    ##########################
    # CORE lint.py FUNCTIONS #
    ##########################
    def test_run_linting_function(self):
        """Run the master run_linting() function in lint.py

        We don't really check any of this code as it's just a series of function calls
        and we're testing each of those individually. This is mostly to check for syntax errors."""
        lint_obj = nf_core.lint.run_linting(self.test_pipeline_dir, False)

    def test_init_PipelineLint(self):
        """Simply create a PipelineLint object.

        This checks that all of the lint test imports are working properly,
        we also check that the git sha was found and that the release flag works properly
        """
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir, True)
        assert "version_consistency" in lint_obj.lint_tests
        assert len(lint_obj.git_sha) > 0

    def test_load_lint_config_not_found(self):
        """Try to load a linting config file that doesn't exist"""
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir)
        lint_obj._load_lint_config()
        assert lint_obj.lint_config == {}

    def test_load_lint_config_ignore_all_tests(self):
        """Try to load a linting config file that ignores all tests"""
        # Make a copy of the test pipeline and create a lint object
        new_pipeline = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
        shutil.copytree(self.test_pipeline_dir, new_pipeline)
        lint_obj = nf_core.lint.PipelineLint(new_pipeline)

        # Make a config file listing all test names
        config_dict = {test_name: False for test_name in lint_obj.lint_tests}
        with open(os.path.join(new_pipeline, ".nf-core-lint.yml"), "w") as fh:
            yaml.dump(config_dict, fh)

        # Load the new lint config file and check
        lint_obj._load_lint_config()
        assert sorted(list(lint_obj.lint_config.keys())) == sorted(lint_obj.lint_tests)

        # Try running linting and make sure that all tests are ignored
        lint_obj._lint_pipeline()
        assert len(lint_obj.passed) == 0
        assert len(lint_obj.warned) == 0
        assert len(lint_obj.failed) == 0
        assert len(lint_obj.ignored) == len(lint_obj.lint_tests)

    def test_load_pipeline_config(self):
        """Load the pipeline Nextflow config"""
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir)
        lint_obj._load_pipeline_config()
        assert lint_obj.config["dag.enabled"] == "true"

    def test_load_conda_env(self):
        """Load the pipeline Conda environment.yml file"""
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir)
        lint_obj._load_conda_environment()
        assert lint_obj.conda_config["channels"] == ["conda-forge", "bioconda", "defaults"]

    def test_list_files_git(self):
        """Test listing pipeline files using `git ls`"""
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir)
        lint_obj._list_files()
        assert os.path.join(self.test_pipeline_dir, "main.nf") in lint_obj.files

    def test_list_files_no_git(self):
        """Test listing pipeline files without `git-ls`"""
        # Create directory with a test file
        tmpdir = tempfile.mkdtemp()
        tmp_fn = os.path.join(tmpdir, "testfile")
        open(tmp_fn, "a").close()
        lint_obj = nf_core.lint.PipelineLint(tmpdir)
        lint_obj._list_files()
        assert tmp_fn in lint_obj.files

    def test_json_output(self):
        """
        Test creation of a JSON file with lint results

        Expected JSON output:
        {
            "nf_core_tools_version": "1.10.dev0",
            "date_run": "2020-06-05 10:56:42",
            "tests_pass": [
                [ 1, "This test passed"],
                [ 2, "This test also passed"]
            ],
            "tests_warned": [
                [ 2, "This test gave a warning"]
            ],
            "tests_failed": [],
            "num_tests_pass": 2,
            "num_tests_warned": 1,
            "num_tests_failed": 0,
            "has_tests_pass": true,
            "has_tests_warned": true,
            "has_tests_failed": false
        }
        """
        # Don't run testing, just fake some testing results
        pipeline = os.path.join(tempfile.mkdtemp(), "test-pipeline")
        lint_obj = nf_core.lint.PipelineLint(pipeline)
        lint_obj.passed.append(("test_one", "This test passed"))
        lint_obj.passed.append(("test_two", "This test also passed"))
        lint_obj.warned.append(("test_three", "This test gave a warning"))

        # Make another temp dir for the JSON output
        json_fn = os.path.join(tempfile.mkdtemp(), "lint_results.json")
        lint_obj._save_json_results(json_fn)

        # Load created JSON file and check its contents
        with open(json_fn, "r") as fh:
            saved_json = json.load(fh)
        assert saved_json["num_tests_pass"] == 2
        assert saved_json["num_tests_warned"] == 1
        assert saved_json["num_tests_ignored"] == 0
        assert saved_json["num_tests_failed"] == 0
        assert saved_json["has_tests_pass"]
        assert saved_json["has_tests_warned"]
        assert not saved_json["has_tests_ignored"]
        assert not saved_json["has_tests_failed"]

    ################################
    # SPECIFIC LINT TEST FUNCTIONS #
    ################################


#    def test_critical_missingfiles_example(self):
#        """Tests for missing nextflow config and main.nf files"""
#        lint_obj = nf_core.lint.run_linting(PATH_CRITICAL_EXAMPLE, False)
#        assert len(lint_obj.failed) == 1
#
#    def test_failing_missingfiles_example(self):
#        """Tests for missing files like Dockerfile or LICENSE"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.check_files_exist()
#        expectations = {"failed": 6, "warned": 2, "passed": 14}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_mit_licence_example_pass(self):
#        """Tests that MIT test works with good MIT licences"""
#        good_lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
#        good_lint_obj.check_licence()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(good_lint_obj, **expectations)
#
#    def test_mit_license_example_with_failed(self):
#        """Tests that MIT test works with bad MIT licences"""
#        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        bad_lint_obj.check_licence()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(bad_lint_obj, **expectations)
#
#    def test_config_variable_example_pass(self):
#        """Tests that config variable existence test works with good pipeline example"""
#        good_lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        good_lint_obj.check_nextflow_config()
#        expectations = {"failed": 0, "warned": 1, "passed": 34}
#        self.assess_lint_status(good_lint_obj, **expectations)
#
#    def test_config_variable_example_with_failed(self):
#        """Tests that config variable existence test fails with bad pipeline example"""
#        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        bad_lint_obj.check_nextflow_config()
#        expectations = {"failed": 19, "warned": 6, "passed": 10}
#        self.assess_lint_status(bad_lint_obj, **expectations)
#
#    @pytest.mark.xfail(raises=AssertionError, strict=True)
#    def test_config_variable_error(self):
#        """Tests that config variable existence test falls over nicely with nextflow can't run"""
#        bad_lint_obj = nf_core.lint.PipelineLint("/non/existant/path")
#        bad_lint_obj.check_nextflow_config()
#
#    def test_actions_wf_branch_pass(self):
#        """Tests that linting for GitHub Actions workflow for branch protection works for a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.pipeline_name = "tools"
#        lint_obj.check_actions_branch_protection()
#        expectations = {"failed": 0, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_branch_fail(self):
#        """Tests that linting for GitHub Actions workflow for branch protection fails for a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.pipeline_name = "tools"
#        lint_obj.check_actions_branch_protection()
#        expectations = {"failed": 2, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_ci_pass(self):
#        """Tests that linting for GitHub Actions CI workflow works for a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.minNextflowVersion = "20.04.0"
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["process.container"] = "'nfcore/tools:0.4'"
#        lint_obj.check_actions_ci()
#        expectations = {"failed": 0, "warned": 0, "passed": 5}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_ci_fail(self):
#        """Tests that linting for GitHub Actions CI workflow fails for a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.minNextflowVersion = "20.04.0"
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["process.container"] = "'nfcore/tools:0.4'"
#        lint_obj.check_actions_ci()
#        expectations = {"failed": 5, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_ci_fail_wrong_NF_version(self):
#        """Tests that linting for GitHub Actions CI workflow fails for a bad NXF version"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.minNextflowVersion = "0.28.0"
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["process.container"] = "'nfcore/tools:0.4'"
#        lint_obj.check_actions_ci()
#        expectations = {"failed": 1, "warned": 0, "passed": 4}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_lint_pass(self):
#        """Tests that linting for GitHub Actions linting wf works for a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.check_actions_lint()
#        expectations = {"failed": 0, "warned": 0, "passed": 3}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_lint_fail(self):
#        """Tests that linting for GitHub Actions linting wf fails for a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.check_actions_lint()
#        expectations = {"failed": 3, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_awstest_pass(self):
#        """Tests that linting for GitHub Actions AWS test wf works for a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.check_actions_awstest()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_awstest_fail(self):
#        """Tests that linting for GitHub Actions AWS test wf fails for a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.check_actions_awstest()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_awsfulltest_pass(self):
#        """Tests that linting for GitHub Actions AWS full test wf works for a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.check_actions_awsfulltest()
#        expectations = {"failed": 0, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_actions_wf_awsfulltest_fail(self):
#        """Tests that linting for GitHub Actions AWS full test wf fails for a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.check_actions_awsfulltest()
#        expectations = {"failed": 1, "warned": 1, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_wrong_license_examples_with_failed(self):
#        """Tests for checking the license test behavior"""
#        for example in PATHS_WRONG_LICENSE_EXAMPLE:
#            lint_obj = nf_core.lint.PipelineLint(example)
#            lint_obj.check_licence()
#            expectations = {"failed": 1, "warned": 0, "passed": 0}
#            self.assess_lint_status(lint_obj, **expectations)
#
#    def test_missing_license_example(self):
#        """Tests for missing license behavior"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_MISSING_LICENSE_EXAMPLE)
#        lint_obj.check_licence()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_readme_pass(self):
#        """Tests that the pipeline README file checks work with a good example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.minNextflowVersion = "20.04.0"
#        lint_obj.files = ["environment.yml"]
#        lint_obj.check_readme()
#        expectations = {"failed": 0, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_readme_warn(self):
#        """Tests that the pipeline README file checks fail  """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.minNextflowVersion = "0.28.0"
#        lint_obj.check_readme()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_readme_fail(self):
#        """Tests that the pipeline README file checks give warnings with a bad example"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.check_readme()
#        expectations = {"failed": 0, "warned": 2, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_dockerfile_pass(self):
#        """Tests if a valid Dockerfile passes the lint checks"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["Dockerfile"]
#        lint_obj.check_docker()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_version_consistency_pass(self):
#        """Tests the workflow version and container version sucessfully"""
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.config["process.container"] = "nfcore/tools:0.4"
#        lint_obj.check_version_consistency()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_version_consistency_with_env_fail(self):
#        """Tests the behaviour, when a git activity is a release
#        and simulate wrong release tag"""
#        os.environ["GITHUB_REF"] = "refs/tags/0.5"
#        os.environ["GITHUB_REPOSITORY"] = "nf-core/testpipeline"
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.config["process.container"] = "nfcore/tools:0.4"
#        lint_obj.check_version_consistency()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_version_consistency_with_numeric_fail(self):
#        """Tests the behaviour, when a git activity is a release
#        and simulate wrong release tag"""
#        os.environ["GITHUB_REF"] = "refs/tags/0.5dev"
#        os.environ["GITHUB_REPOSITORY"] = "nf-core/testpipeline"
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.config["process.container"] = "nfcore/tools:0.4"
#        lint_obj.check_version_consistency()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_version_consistency_with_no_docker_version_fail(self):
#        """Tests the behaviour, when a git activity is a release
#        and simulate wrong missing docker version tag"""
#        os.environ["GITHUB_REF"] = "refs/tags/0.4"
#        os.environ["GITHUB_REPOSITORY"] = "nf-core/testpipeline"
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.config["process.container"] = "nfcore/tools"
#        lint_obj.check_version_consistency()
#        expectations = {"failed": 1, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_version_consistency_with_env_pass(self):
#        """Tests the behaviour, when a git activity is a release
#        and simulate correct release tag"""
#        os.environ["GITHUB_REF"] = "refs/tags/0.4"
#        os.environ["GITHUB_REPOSITORY"] = "nf-core/testpipeline"
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.config["process.container"] = "nfcore/tools:0.4"
#        lint_obj.check_version_consistency()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_env_pass(self):
#        """ Tests the conda environment config checks with a working example """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        with open(os.path.join(PATH_WORKING_EXAMPLE, "environment.yml"), "r") as fh:
#            lint_obj.conda_config = yaml.safe_load(fh)
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 0, "warned": 4, "passed": 5}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_env_fail(self):
#        """ Tests the conda environment config fails with a bad example """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        with open(os.path.join(PATH_WORKING_EXAMPLE, "environment.yml"), "r") as fh:
#            lint_obj.conda_config = yaml.safe_load(fh)
#        lint_obj.conda_config["dependencies"] = ["fastqc", "multiqc=0.9", "notapackaage=0.4"]
#        lint_obj.pipeline_name = "not_tools"
#        lint_obj.config["manifest.version"] = "0.23"
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 3, "warned": 1, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    @mock.patch("requests.get")
#    @pytest.mark.xfail(raises=ValueError, strict=True)
#    def test_conda_env_timeout(self, mock_get):
#        """ Tests the conda environment handles API timeouts """
#        # Define the behaviour of the request get mock
#        mock_get.side_effect = requests.exceptions.Timeout()
#        # Now do the test
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.conda_config["channels"] = ["bioconda"]
#        lint_obj.check_anaconda_package("multiqc=1.6")
#
#    def test_conda_env_skip(self):
#        """ Tests the conda environment config is skipped when not needed """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 0, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_dockerfile_pass(self):
#        """ Tests the conda Dockerfile test works with a working example """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.version = "1.11"
#        lint_obj.files = ["environment.yml", "Dockerfile"]
#        with open(os.path.join(PATH_WORKING_EXAMPLE, "Dockerfile"), "r") as fh:
#            lint_obj.dockerfile = fh.read().splitlines()
#        lint_obj.conda_config["name"] = "nf-core-tools-0.4"
#        lint_obj.check_conda_dockerfile()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_dockerfile_fail(self):
#        """ Tests the conda Dockerfile test fails with a bad example """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.version = "1.11"
#        lint_obj.files = ["environment.yml", "Dockerfile"]
#        lint_obj.conda_config["name"] = "nf-core-tools-0.4"
#        lint_obj.dockerfile = ["fubar"]
#        lint_obj.check_conda_dockerfile()
#        expectations = {"failed": 5, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_dockerfile_skip(self):
#        """ Tests the conda Dockerfile test is skipped when not needed """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.check_conda_dockerfile()
#        expectations = {"failed": 0, "warned": 0, "passed": 0}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_pip_no_version_fail(self):
#        """ Tests the pip dependency version definition is present """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["multiqc"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 1, "warned": 0, "passed": 1}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_pip_package_not_latest_warn(self):
#        """ Tests the pip dependency version definition is present """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["multiqc==1.4"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 0, "warned": 1, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    @mock.patch("requests.get")
#    def test_pypi_timeout_warn(self, mock_get):
#        """Tests the PyPi connection and simulates a request timeout, which should
#        return in an addiional warning in the linting"""
#        # Define the behaviour of the request get mock
#        mock_get.side_effect = requests.exceptions.Timeout()
#        # Now do the test
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["multiqc==1.5"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 0, "warned": 1, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    @mock.patch("requests.get")
#    def test_pypi_connection_error_warn(self, mock_get):
#        """Tests the PyPi connection and simulates a connection error, which should
#        result in an additional warning, as we cannot test if dependent module is latest"""
#        # Define the behaviour of the request get mock
#        mock_get.side_effect = requests.exceptions.ConnectionError()
#        # Now do the test
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["multiqc==1.5"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 0, "warned": 1, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_pip_dependency_fail(self):
#        """ Tests the PyPi API package information query """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["notpresent==1.5"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 1, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_conda_dependency_fails(self):
#        """Tests that linting fails, if conda dependency
#        package version is not available on Anaconda.
#        """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": ["openjdk=0.0.0"]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 1, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_pip_dependency_fails(self):
#        """Tests that linting fails, if conda dependency
#        package version is not available on Anaconda.
#        """
#        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        lint_obj.files = ["environment.yml"]
#        lint_obj.pipeline_name = "tools"
#        lint_obj.config["manifest.version"] = "0.4"
#        lint_obj.conda_config = {"name": "nf-core-tools-0.4", "dependencies": [{"pip": ["multiqc==0.0"]}]}
#        lint_obj.check_conda_env_yaml()
#        expectations = {"failed": 1, "warned": 0, "passed": 2}
#        self.assess_lint_status(lint_obj, **expectations)
#
#    def test_pipeline_name_pass(self):
#        """Tests pipeline name good pipeline example: lower case, no punctuation"""
#        # good_lint_obj = nf_core.lint.run_linting(PATH_WORKING_EXAMPLE)
#        good_lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        good_lint_obj.pipeline_name = "tools"
#        good_lint_obj.check_pipeline_name()
#        expectations = {"failed": 0, "warned": 0, "passed": 1}
#        self.assess_lint_status(good_lint_obj, **expectations)
#
#    def test_pipeline_name_critical(self):
#        """Tests that warning is returned for pipeline not adhering to naming convention"""
#        critical_lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
#        critical_lint_obj.pipeline_name = "Tools123"
#        critical_lint_obj.check_pipeline_name()
#        expectations = {"failed": 0, "warned": 1, "passed": 0}
#        self.assess_lint_status(critical_lint_obj, **expectations)
#
