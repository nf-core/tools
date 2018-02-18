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
import nf_core
import nf_core.lint
from nose.tools import raises

def pf(wd, path):
    return os.path.join(wd, path)

WD = os.path.dirname(__file__)
PATH_CRITICAL_EXAMPLE =  pf(WD, 'lint_examples/critical_example')
PATH_FAILING_EXAMPLE = pf(WD, 'lint_examples/failing_example')

class TestLint(unittest.TestCase):
    """Class for lint tests"""

    @raises(AssertionError)
    def test_critical_missingfiles_example(self):
        """Tests for missing nextflow config and main.nf files"""
        lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
        lint_obj.check_files_exist()

    def test_failing_missingfiles_example(self):
        """Tests for missing files like Dockerfile or LICENSE"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_files_exist()
        assert len(lint_obj.failed) == 7, "Expected 7 missing file FAIL, but found %r" % len(lint_obj.failed)
        assert len(lint_obj.warned) == 2, "Expected 2 missing file WARN, but found %r" % len(lint_obj.passed)
        assert len(lint_obj.passed) == 3, "Expected 3 missing file PASS, but found %r" % len(lint_obj.passed)

    def test_mit_licence_example_pass(self):
        """Tests that MIT test works with good and bad MIT licences"""
        good_lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
        good_lint_obj.check_licence()
        assert len(good_lint_obj.failed) == 0, "Expected 0 MIT FAIL, but found %r" % len(good_lint_obj.failed)
        assert len(good_lint_obj.warned) == 0, "Expected 0 MIT WARN, but found %r" % len(good_lint_obj.passed)
        assert len(good_lint_obj.passed) == 1, "Expected 1 MIT PASS, but found %r" % len(good_lint_obj.passed)
        bad_lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        bad_lint_obj.check_licence()
        assert len(bad_lint_obj.failed) == 1, "Expected 1 MIT FAIL, but found %r" % len(bad_lint_obj.failed)
        assert len(bad_lint_obj.warned) == 0, "Expected 0 MIT WARN, but found %r" % len(bad_lint_obj.passed)
        assert len(bad_lint_obj.passed) == 0, "Expected 0 MIT PASS, but found %r" % len(bad_lint_obj.passed)
