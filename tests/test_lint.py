"""Some tests covering the linting code."""

import fnmatch
import json
import os
import shutil
import tempfile
import unittest

import yaml

import nf_core.create
import nf_core.lint

from .utils import with_temporary_folder


class TestLint(unittest.TestCase):
    """Class for lint tests"""

    def setUp(self):
        """Function that runs at start of tests for common resources

        Use nf_core.create() to make a pipeline that we can use for testing
        """

        self.tmp_dir = tempfile.mkdtemp()
        self.test_pipeline_dir = os.path.join(self.tmp_dir, "nf-core-testpipeline")
        self.create_obj = nf_core.create.PipelineCreate(
            "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=self.test_pipeline_dir, plain=True
        )
        self.create_obj.init_pipeline()

        # Base lint object on this directory
        self.lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if os.path.exists(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def _make_pipeline_copy(self):
        """Make a copy of the test pipeline that can be edited

        Returns: Path to new temp directory with pipeline"""
        new_pipeline = os.path.join(self.tmp_dir, "nf-core-testpipeline-copy")
        shutil.copytree(self.test_pipeline_dir, new_pipeline)
        return new_pipeline

    ##########################
    # CORE lint.py FUNCTIONS #
    ##########################
    def test_run_linting_function(self):
        """Run the master run_linting() function in lint.py

        We don't really check any of this code as it's just a series of function calls
        and we're testing each of those individually. This is mostly to check for syntax errors."""
        nf_core.lint.run_linting(self.test_pipeline_dir, False)

    def test_init_pipeline_lint(self):
        """Simply create a PipelineLint object.

        This checks that all of the lint test imports are working properly,
        we also check that the git sha was found and that the release flag works properly
        """
        lint_obj = nf_core.lint.PipelineLint(self.test_pipeline_dir, True)

        # Tests that extra test is added for release mode
        assert "version_consistency" in lint_obj.lint_tests

        # Tests that parent nf_core.utils.Pipeline class __init__() is working to find git hash
        assert len(lint_obj.git_sha) > 0

    def test_load_lint_config_not_found(self):
        """Try to load a linting config file that doesn't exist"""
        self.lint_obj._load_lint_config()
        assert self.lint_obj.lint_config == {}

    def test_load_lint_config_ignore_all_tests(self):
        """Try to load a linting config file that ignores all tests"""

        # Make a copy of the test pipeline and create a lint object
        new_pipeline = self._make_pipeline_copy()
        lint_obj = nf_core.lint.PipelineLint(new_pipeline)

        # Make a config file listing all test names
        config_dict = {"lint": {test_name: False for test_name in lint_obj.lint_tests}}
        with open(os.path.join(new_pipeline, ".nf-core.yml"), "w") as fh:
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

    @with_temporary_folder
    def test_json_output(self, tmp_dir):
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
        self.lint_obj.passed.append(("test_one", "This test passed"))
        self.lint_obj.passed.append(("test_two", "This test also passed"))
        self.lint_obj.warned.append(("test_three", "This test gave a warning"))

        # Make a temp dir for the JSON output
        json_fn = os.path.join(tmp_dir, "lint_results.json")
        self.lint_obj._save_json_results(json_fn)

        # Load created JSON file and check its contents
        with open(json_fn) as fh:
            try:
                saved_json = json.load(fh)
            except json.JSONDecodeError as e:
                raise UserWarning(f"Unable to load JSON file '{json_fn}' due to error {e}")
        assert saved_json["num_tests_pass"] > 0
        assert saved_json["num_tests_warned"] > 0
        assert saved_json["num_tests_ignored"] == 0
        assert saved_json["num_tests_failed"] == 0
        assert saved_json["has_tests_pass"]
        assert saved_json["has_tests_warned"]
        assert not saved_json["has_tests_ignored"]
        assert not saved_json["has_tests_failed"]

    def test_wrap_quotes(self):
        md = self.lint_obj._wrap_quotes(["one", "two", "three"])
        assert md == "`one` or `two` or `three`"

    def test_sphinx_md_files(self):
        """Check that we have .md files for all lint module code,
        and that there are no unexpected files (eg. deleted lint tests)"""

        docs_basedir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "api", "_src", "pipeline_lint_tests"
        )

        # Get list of existing .md files
        existing_docs = []
        for fn in os.listdir(docs_basedir):
            if fnmatch.fnmatch(fn, "*.md") and not fnmatch.fnmatch(fn, "index.md"):
                existing_docs.append(os.path.join(docs_basedir, fn))

        # Check .md files against each test name
        lint_obj = nf_core.lint.PipelineLint("", True)
        for test_name in lint_obj.lint_tests:
            fn = os.path.join(docs_basedir, f"{test_name}.md")
            assert os.path.exists(fn), f"Could not find lint docs .md file: {fn}"
            existing_docs.remove(fn)

        # Check that we have no remaining .md files that we didn't expect
        assert len(existing_docs) == 0, f"Unexpected lint docs .md files found: {', '.join(existing_docs)}"

    #######################
    # SPECIFIC LINT TESTS #
    #######################
    from .lint.actions_awsfulltest import (  # type: ignore[misc]
        test_actions_awsfulltest_fail,
        test_actions_awsfulltest_pass,
        test_actions_awsfulltest_warn,
    )
    from .lint.actions_awstest import (  # type: ignore[misc]
        test_actions_awstest_fail,
        test_actions_awstest_pass,
    )
    from .lint.actions_ci import (  # type: ignore[misc]
        test_actions_ci_fail_wrong_nf,
        test_actions_ci_fail_wrong_trigger,
        test_actions_ci_pass,
    )
    from .lint.actions_schema_validation import (  # type: ignore[misc]
        test_actions_schema_validation_fails_for_additional_property,
        test_actions_schema_validation_missing_jobs,
        test_actions_schema_validation_missing_on,
    )
    from .lint.configs import (  # type: ignore[misc]
        test_ignore_base_config,
        test_ignore_modules_config,
        test_superfluous_withname_in_base_config_fails,
        test_superfluous_withname_in_modules_config_fails,
        test_withname_in_modules_config,
    )
    from .lint.files_exist import (  # type: ignore[misc]
        test_files_exist_depreciated_file,
        test_files_exist_fail_conditional,
        test_files_exist_missing_config,
        test_files_exist_missing_main,
        test_files_exist_pass,
        test_files_exist_pass_conditional,
    )
    from .lint.files_unchanged import (  # type: ignore[misc]
        test_files_unchanged_fail,
        test_files_unchanged_pass,
    )
    from .lint.merge_markers import test_merge_markers_found  # type: ignore[misc]
    from .lint.modules_json import test_modules_json_pass  # type: ignore[misc]
    from .lint.multiqc_config import (  # type: ignore[misc]
        test_multiqc_config_exists,
        test_multiqc_config_ignore,
        test_multiqc_config_missing_report_section_order,
        test_multiqc_config_report_comment_fail,
        test_multiqc_config_report_comment_release_fail,
        test_multiqc_config_report_comment_release_succeed,
        test_multiqc_incorrect_export_plots,
    )
    from .lint.nextflow_config import (  # type: ignore[misc]
        test_allow_params_reference_in_main_nf,
        test_catch_params_assignment_in_main_nf,
        test_default_values_fail,
        test_default_values_float,
        test_default_values_float_fail,
        test_default_values_ignored,
        test_default_values_match,
        test_nextflow_config_bad_name_fail,
        test_nextflow_config_dev_in_release_mode_failed,
        test_nextflow_config_example_pass,
        test_nextflow_config_missing_test_profile_failed,
    )
    from .lint.nfcore_yml import (  # type: ignore[misc]
        test_nfcore_yml_fail_nfcore_version,
        test_nfcore_yml_fail_repo_type,
        test_nfcore_yml_pass,
    )
    from .lint.template_strings import (  # type: ignore[misc]
        test_template_strings,
        test_template_strings_ignore_file,
        test_template_strings_ignored,
    )
    from .lint.version_consistency import test_version_consistency  # type: ignore[misc]


# TODO nf-core: Assess and strip out if no longer required for DSL2

#    def test_critical_missingfiles_example(self):
#        """Tests for missing nextflow config and main.nf files"""
#        lint_obj = nf_core.lint.run_linting(PATH_CRITICAL_EXAMPLE, False)
#        assert len(lint_obj.failed) > 0
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
