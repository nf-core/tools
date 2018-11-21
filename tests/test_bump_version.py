#!/usr/bin/env python
"""Some tests covering the bump_version code.
"""
import os
import pytest
import shutil
import unittest
import nf_core.lint, nf_core.bump_version

WD = os.path.dirname(__file__)
PATH_WORKING_EXAMPLE = os.path.join(WD, 'lint_examples/minimal_working_example')


@pytest.mark.datafiles(PATH_WORKING_EXAMPLE)
def test_working_bump_pipeline_version(datafiles):
    """ Test that making a release with the working example files works """
    lint_obj = nf_core.lint.PipelineLint(str(datafiles))
    lint_obj.pipeline_name = 'tools'
    lint_obj.config['manifest.version'] = '0.4'
    lint_obj.files = ['nextflow.config', 'Dockerfile', 'environment.yml']
    nf_core.bump_version.bump_pipeline_version(lint_obj, '1.1')

@pytest.mark.datafiles(PATH_WORKING_EXAMPLE)
def test_dev_bump_pipeline_version(datafiles):
    """ Test that making a release works with a dev name and a leading v """
    lint_obj = nf_core.lint.PipelineLint(str(datafiles))
    lint_obj.pipeline_name = 'tools'
    lint_obj.config['manifest.version'] = '0.4'
    lint_obj.files = ['nextflow.config', 'Dockerfile', 'environment.yml']
    nf_core.bump_version.bump_pipeline_version(lint_obj, 'v1.2dev')

@pytest.mark.datafiles(PATH_WORKING_EXAMPLE)
@pytest.mark.xfail(raises=SyntaxError)
def test_pattern_not_found(datafiles):
    """ Test that making a release raises and error if a pattern isn't found """
    lint_obj = nf_core.lint.PipelineLint(str(datafiles))
    lint_obj.pipeline_name = 'tools'
    lint_obj.config['manifest.version'] = '0.5'
    lint_obj.files = ['nextflow.config', 'Dockerfile', 'environment.yml']
    nf_core.bump_version.bump_pipeline_version(lint_obj, '1.2dev')

@pytest.mark.datafiles(PATH_WORKING_EXAMPLE)
@pytest.mark.xfail(raises=SyntaxError)
def test_multiple_patterns_found(datafiles):
    """ Test that making a release raises if a version number is found twice """
    lint_obj = nf_core.lint.PipelineLint(str(datafiles))
    with open(os.path.join(str(datafiles), 'nextflow.config'), "a") as nfcfg:
        nfcfg.write("manifest.version = '0.4'")
    lint_obj.pipeline_name = 'tools'
    lint_obj.config['manifest.version'] = '0.4'
    lint_obj.files = ['nextflow.config', 'Dockerfile', 'environment.yml']
    nf_core.bump_version.bump_pipeline_version(lint_obj, '1.2dev')

@pytest.mark.datafiles(PATH_WORKING_EXAMPLE)
def test_successfull_nextflow_version_bump(datafiles):
    lint_obj = nf_core.lint.PipelineLint(str(datafiles))
    lint_obj.pipeline_name = 'tools'
    lint_obj.config['manifest.nextflowVersion'] = '0.32.0'
    nf_core.bump_version.bump_nextflow_version(lint_obj, '0.40')
    lint_obj_new = nf_core.lint.PipelineLint(str(datafiles))
    lint_obj_new.check_nextflow_config()
    assert lint_obj_new.config['manifest.nextflowVersion'] == "'>=0.40'"