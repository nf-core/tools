#!/usr/bin/env python

import os
import yaml
import nf_core.lint

def test_mit_licence_pass(self):
    """Lint test: check a valid MIT licence"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.licence()
    assert results["passed"] == ["Licence check passed"]

def test_mit_licence_fail(self):
    """Lint test: invalid MIT licence"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    fh = open(os.path.join(new_pipeline, "LICENSE"), "a")
    fh.write("[year]")
    fh.close()
    
    results = lint_obj.licence()
    assert results["failed"] == ["Licence file contains placeholders: {}".format(os.path.join(new_pipeline, "LICENSE"))]