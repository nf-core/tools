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

MAX_PASS_CHECKS = 14

class TestLint(unittest.TestCase):
    """Class for lint tests"""

    def assess_lint_status(self, lint_obj, **expected):
        """Little helper function for assessing the lint
        object status lists"""
        for list_type, expect in expected.items():
            observed = len(getattr(lint_obj, list_type))
            self.assertEqual(observed, expect, "Expected {} files in \'{}\', but found {}.".format(expect, list_type.upper(), observed))

    def test_call_lint_pipeline(self):
        """Test the main execution function of PipelineLint
        This should not result in any exception for the minimal
        working example"""
        lint_obj = nf_core.lint.PipelineLint(PATH_WORKING_EXAMPLE)
        lint_obj.lint_pipeline()
        expectations = {"failed": 0, "warned": 0, "passed": MAX_PASS_CHECKS}
        self.assess_lint_status(lint_obj, **expectations)

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
        expectations = {"failed": 6, "warned": 2, "passed": len(listfiles(PATH_WORKING_EXAMPLE)) - 6 - 2}
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
