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
    def test_critical_example(self):
        """Tests for missing nextflow config and main.nf files"""
        lint_obj = nf_core.lint.PipelineLint(PATH_CRITICAL_EXAMPLE)
        lint_obj.check_files_exist()

    def test_failing_example(self):
        """Tests for missing files like Dockerfile or LICENSE"""
        lint_obj = nf_core.lint.PipelineLint(PATH_FAILING_EXAMPLE)
        lint_obj.check_files_exist()
        assert len(lint_obj.failed) == 7, "Expected 6 files missing, but found %r" % len(lint_obj.failed)
        assert len(lint_obj.passed) == 2, "Expected 6 files missing, but found %r" % len(lint_obj.passed)
    
    