#!/usr/bin/env python
"""Some tests covering the bump_version code.
"""
import os
import yaml

import nf_core.bump_version
import nf_core.create
import nf_core.utils


# pass tmp_path as argument, which is a pytest feature
# see: https://docs.pytest.org/en/latest/how-to/tmp_path.html#the-tmp-path-fixture
def test_bump_pipeline_version(datafiles, tmp_path):
    """Test that making a release with the working example files works"""

    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tmp_path, "nf-core-testpipeline")
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


def test_dev_bump_pipeline_version(datafiles, tmp_path):
    """Test that making a release works with a dev name and a leading v"""
    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tmp_path, "nf-core-testpipeline")
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


def test_bump_nextflow_version(datafiles, tmp_path):
    # Get a workflow and configs
    test_pipeline_dir = os.path.join(tmp_path, "nf-core-testpipeline")
    create_obj = nf_core.create.PipelineCreate(
        "testpipeline", "This is a test pipeline", "Test McTestFace", outdir=test_pipeline_dir
    )
    create_obj.init_pipeline()
    pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)
    pipeline_obj._load()

    # Bump the version number
    nf_core.bump_version.bump_nextflow_version(pipeline_obj, "21.10.3")
    new_pipeline_obj = nf_core.utils.Pipeline(test_pipeline_dir)

    # Check nextflow.config
    new_pipeline_obj._load_pipeline_config()
    assert new_pipeline_obj.nf_config["manifest.nextflowVersion"].strip("'\"") == "!>=21.10.3"

    # Check .github/workflows/ci.yml
    with open(new_pipeline_obj._fp(".github/workflows/ci.yml")) as fh:
        ci_yaml = yaml.safe_load(fh)
    assert ci_yaml["jobs"]["test"]["strategy"]["matrix"]["include"][0]["NXF_VER"] == "21.10.3"

    # Check README.md
    with open(new_pipeline_obj._fp("README.md")) as fh:
        readme = fh.read().splitlines()
    assert (
        "[![Nextflow](https://img.shields.io/badge/nextflow%20DSL2-%E2%89%A5{}-23aa62.svg?labelColor=000000)](https://www.nextflow.io/)".format(
            "21.10.3"
        )
        in readme
    )
