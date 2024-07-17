"""Some tests covering the linting code."""

import json
from pathlib import Path

import yaml

import nf_core.pipelines.create.create
import nf_core.pipelines.lint

from ..test_pipelines import TestPipelines
from ..utils import with_temporary_folder


class TestLint(TestPipelines):
    """Class for lint tests"""

    def setUp(self) -> None:
        super().setUp()
        self.lint_obj = nf_core.pipelines.lint.PipelineLint(self.pipeline_dir)

    ##########################
    # CORE lint.py FUNCTIONS #
    ##########################
    def test_run_linting_function(self):
        """Run the master run_linting() function in lint.py

        We don't really check any of this code as it's just a series of function calls
        and we're testing each of those individually. This is mostly to check for syntax errors."""
        nf_core.pipelines.lint.run_linting(self.pipeline_dir, False)

    def test_init_pipeline_lint(self):
        """Simply create a PipelineLint object.

        This checks that all of the lint test imports are working properly,
        we also check that the git sha was found and that the release flag works properly
        """
        lint_obj = nf_core.pipelines.lint.PipelineLint(self.pipeline_dir, True)

        # Tests that extra test is added for release mode
        assert "version_consistency" in lint_obj.lint_tests
        assert lint_obj.git_sha
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
        lint_obj = nf_core.pipelines.lint.PipelineLint(new_pipeline)

        # Make a config file listing all test names
        config_dict = {"lint": {test_name: False for test_name in lint_obj.lint_tests}}
        with open(Path(new_pipeline, ".nf-core.yml"), "w") as fh:
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
        json_fn = Path(tmp_dir, "lint_results.json")
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

        docs_basedir = Path(Path(__file__).parent.parent.parent, "docs", "api", "_src", "pipeline_lint_tests")

        # Get list of existing .md files
        existing_docs = []
        existing_docs = [
            str(Path(docs_basedir, fn))
            for fn in Path(docs_basedir).iterdir()
            if fn.match("*.md") and not fn.match("index.md")
        ]

        # Check .md files against each test name
        lint_obj = nf_core.pipelines.lint.PipelineLint("", True)
        for test_name in lint_obj.lint_tests:
            fn = Path(docs_basedir, f"{test_name}.md")
            assert fn.exists(), f"Could not find lint docs .md file: {fn}"
            existing_docs.remove(str(fn))

        # Check that we have no remaining .md files that we didn't expect
        assert len(existing_docs) == 0, f"Unexpected lint docs .md files found: {', '.join(existing_docs)}"

    #######################
    # SPECIFIC LINT TESTS #
    #######################

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
        test_files_exist_deprecated_file,
        test_files_exist_fail_conditional,
        test_files_exist_missing_config,
        test_files_exist_missing_main,
        test_files_exist_pass,
        test_files_exist_pass_conditional,
        test_files_exist_pass_conditional_nfschema,
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
