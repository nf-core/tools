#!/usr/bin/env python
"""Some tests covering the bump_version code.
"""
import os
import pytest
import nf_core.lint, nf_core.create
import tempfile
import unittest

WD = os.path.dirname(__file__)
PIPELINE_NAME = 'nf-core/test'
PIPELINE_DESCRIPTION = 'just for 4w3s0m3 tests'
PIPELINE_VERSION = '1.0.0'

class NfcoreCreateTest(unittest.TestCase):

    def setUp(self):
        self.tmppath = tempfile.mkdtemp()
        self.pipeline = nf_core.create.PipelineCreate(name=PIPELINE_NAME,
                                      description=PIPELINE_DESCRIPTION,
                                      new_version=PIPELINE_VERSION,
                                      no_git=False,
                                      force=True,
                                      outdir=self.tmppath)


    def test_pipeline_creation(self):
        assert self.pipeline.name == PIPELINE_NAME
        assert self.pipeline.description == PIPELINE_DESCRIPTION
        assert self.pipeline.new_version == PIPELINE_VERSION

    def test_pipeline_creation_initiation(self):
        self.pipeline.init_pipeline()
        assert (os.path.isdir(os.path.join(self.pipeline.outdir, '.git')))
