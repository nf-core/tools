import pytest
import unittest
import tempfile
import os
import shutil

import nf_core.create
import nf_core.lint


def test_nextflow_config_example_pass(self):
    """Tests that config variable existence test works with good pipeline example"""
    self.lint_obj._load_pipeline_config()
    result = self.lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["warned"]) == 0


def test_nextflow_config_bad_name_fail(self):
    """Tests that config variable existence test fails with bad pipeline name"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.nf_config["manifest.name"] = "bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0


def test_nextflow_config_dev_in_release_mode_failed(self):
    """Tests that config variable existence test fails with dev version in release mode"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.release_mode = True
    lint_obj.nf_config["manifest.version"] = "dev_is_bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0
