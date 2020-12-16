#!/usr/bin/env python
"""Some tests covering the bump_version code.
"""
import os
import tempfile
import yaml

import nf_core.bump_version
import nf_core.create
import nf_core.utils


def test_bump_pipeline_version(datafiles):
    """ Test that making a release with the working example files works """
    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
    create_obj = nf_core.create.PipelineCreate(
        "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=test_pipeline_dir
    )
    create_obj.init_pipeline()
    pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)
    pipeline_obj._load()

    # Bump the version number
    nf_core.bump_version.bump_pipeline_version(pipeline_obj, "1.1")
    new_pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)

    # Check nextflow.config
    new_pipeline_obj._load_pipeline_config()
    assert new_pipeline_obj.nf_config["manifest.version"].strip("'\"") == "1.1"
    # assert new_pipeline_obj.nf_config["process.container"].strip("'\"") == "nfcore/testpipeline:1.1"

    # # Check .github/workflows/ci.yml
    # with open(new_pipeline_obj._fp(".github/workflows/ci.yml")) as fh:
    #     ci_yaml = yaml.safe_load(fh)
    # assert ci_yaml["jobs"]["test"]["steps"][2]["run"] == "docker build --no-cache . -t nfcore/testpipeline:1.1"
    # assert "docker tag nfcore/testpipeline:dev nfcore/testpipeline:1.1" in ci_yaml["jobs"]["test"]["steps"][3]["run"]

    # # Check environment.yml
    # with open(new_pipeline_obj._fp("environment.yml")) as fh:
    #     conda_env = yaml.safe_load(fh)
    # assert conda_env["name"] == "nf-core-testpipeline-1.1"

    # # Check Dockerfile
    # with open(new_pipeline_obj._fp("Dockerfile")) as fh:
    #     dockerfile = fh.read().splitlines()
    # assert "ENV PATH /opt/conda/envs/nf-core-testpipeline-1.1/bin:$PATH" in dockerfile
    # assert "RUN conda env export --name nf-core-testpipeline-1.1 > nf-core-testpipeline-1.1.yml" in dockerfile


def test_dev_bump_pipeline_version(datafiles):
    """ Test that making a release works with a dev name and a leading v """
    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
    create_obj = nf_core.create.PipelineCreate(
        "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=test_pipeline_dir
    )
    create_obj.init_pipeline()
    pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)
    pipeline_obj._load()

    # Bump the version number
    nf_core.bump_version.bump_pipeline_version(pipeline_obj, "v1.2dev")
    new_pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)

    # Check the pipeline config
    new_pipeline_obj._load_pipeline_config()
    assert new_pipeline_obj.nf_config["manifest.version"].strip("'\"") == "1.2dev"
    # assert new_pipeline_obj.nf_config["process.container"].strip("'\"") == "nfcore/testpipeline:dev"


def test_bump_nextflow_version(datafiles):
    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tempfile.mkdtemp(), "nf-core-testpipeline")
    create_obj = nf_core.create.PipelineCreate(
        "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=test_pipeline_dir
    )
    create_obj.init_pipeline()
    pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)
    pipeline_obj._load()

    # Bump the version number
    nf_core.bump_version.bump_nextflow_version(pipeline_obj, "19.10.3-edge")
    new_pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)

    # Check nextflow.config
    new_pipeline_obj._load_pipeline_config()
    assert new_pipeline_obj.nf_config["manifest.nextflowVersion"].strip("'\"") == "!>=20.11.0-edge"

    # # Check .github/workflows/ci.yml
    # with open(new_pipeline_obj._fp(".github/workflows/ci.yml")) as fh:
    #     ci_yaml = yaml.safe_load(fh)
    # assert ci_yaml["jobs"]["test"]["strategy"]["matrix"]["nxf_ver"][0] == "19.10.3-edge"

    # Check README.md
    with open(new_pipeline_obj._fp("README.md")) as fh:
        readme = fh.read().splitlines()
    assert (
        #"[![Nextflow](https://img.shields.io/badge/nextflow-%E2%89%A5{}-brightgreen.svg)](https://www.nextflow.io/)".format( 
        "[![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A5{}-23aa62.svg?labelColor=000000)](https://www.nextflow.io/)".format( 
            "19.10.3-edge".replace('-','--')
        )
        in readme
        
    )
