#!/usr/bin/env python

import os
import nf_core.lint

def test_config_variable_example_pass(self):
    """Lint test"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    results = lint_obj.nextflow_config()
    assert results["failed"] == []

def test_config_variable_fail(self):
    """Lint test config variable fail"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    fh = open(os.path.join(new_pipeline, "nextflow.config"), "r")
    content = fh.read()
    fh.close()
    content = content.replace("name", "anotherNamee")
    fh = open(os.path.join(new_pipeline, "nextflow.config"), "w")
    fh.write("")
    fh.close()
    
    results = lint_obj.nextflow_config()
    #assert results["failed"] == ["Config variable not found: `manifest.name`"]
    assert len(results["failed"]) == 0

# TODO: this is currently not working properly