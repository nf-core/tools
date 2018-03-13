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
import unittest
import nf_core.lint
from nose.tools import raises

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


MAX_PASS_CHECKS = 35

class TestLint(unittest.TestCase):
    """Class for lint tests"""

    def assess_lint_status(self, lint_obj, **expected):
        """Little helper function for assessing the lint
        object status lists"""
        for list_type, expect in expected.items():
            observed = len(getattr(lint_obj, list_type))
            self.assertEqual(observed, expect, "Expected {} tests in '{}', but found {}.\n{}".format(expect, list_type.upper(), observed, getattr(lint_obj, list_type)))

    def test_call_lint_pipeline(self):
        """Test the main execution function of PipelineLint
        This should not result in any exception for the minimal
        working example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.lint_pipeline()
        expectations = {"failed": 0, "warned": 0, "passed": MAX_PASS_CHECKS}
        self.assess_lint_status(lint_obj, **expectations)
        lint_obj.print_results()

    def test_failing_dockerfile_example(self):
        """Tests for empty Dockerfile"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_docker()
        self.assess_lint_status(lint_obj, failed=1)

    @raises(AssertionError)
    def test_critical_missingfiles_example(self):
        """Tests for missing nextflow config and main.nf files"""
        lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
        lint_obj.check_files_exist()

    def test_failing_missingfiles_example(self):
        """Tests for missing files like Dockerfile or LICENSE"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_files_exist()
        expectations = {"failed": 4, "warned": 2, "passed": len(listfiles(PATH_WORKING_EXAMPLE)) - 4 - 2}
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
        good_lint_obj.check_config_vars()
        expectations = {"failed": 0, "warned": 0, "passed": 18}
        self.assess_lint_status(good_lint_obj, **expectations)

    def test_config_variable_example_with_failed(self):
        """Tests that config variable existence test works with bad pipeline example"""
        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        bad_lint_obj.check_config_vars()
        expectations = {"failed": 11, "warned": 7, "passed": 0}
        self.assess_lint_status(bad_lint_obj, **expectations)

    def test_ci_conf_pass(self):
        """Tests that the continous integration config checks work with a good example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config['params.nf_required_version'] = '0.27.0'
        lint_obj.check_ci_config()
        expectations = {"failed": 0, "warned": 0, "passed": 2}
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
        lint_obj.config['params.nf_required_version'] = '0.27.0'
        lint_obj.check_readme()
        expectations = {"failed": 0, "warned": 0, "passed": 1}
        self.assess_lint_status(lint_obj, **expectations)

    def test_readme_warn(self):
        """Tests that the pipeline README file checks fail  """
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.config['params.nf_required_version'] = '0.28.0'
        lint_obj.check_readme()
        expectations = {"failed": 1, "warned": 0, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)

    def test_readme_fail(self):
        """Tests that the pipeline README file checks give warnings with a bad example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_readme()
        expectations = {"failed": 0, "warned": 1, "passed": 0}
        self.assess_lint_status(lint_obj, **expectations)
