#!/usr/bin/env python
"""Some tests covering the pipeline creation sub command.
"""
import pytest
import nf_core.lint, nf_core.licences
import unittest


PL_WITH_LICENSES = 'nf-core/hlatyping'


class WorkflowLicensesTest(unittest.TestCase):
    """ A class that performs tests on the workflow license
    retrieval functionality of nf-core tools."""

    def setUp(self):
        self.license_obj = nf_core.licences.WorkflowLicences(
            pipeline=PL_WITH_LICENSES
        )

    def test_fetch_licenses_successful(self):
        self.license_obj.fetch_conda_licences()
        self.license_obj.print_licences()

    @pytest.mark.xfail(raises=LookupError)
    def test_errorness_pipeline_name(self):
        self.license_obj.pipeline = 'notpresent'
        self.license_obj.fetch_conda_licences()
        self.license_obj.print_licences()
