import os

import pytest

import nf_core.subworkflows


def test_subworkflows_create_succeed(self):
    """Succeed at creating a subworkflow from the template inside a pipeline"""
    subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
        self.pipeline_dir, "test_subworkflow_local", "@author", True
    )
    subworkflow_create.create()
    assert os.path.exists(os.path.join(self.pipeline_dir, "subworkflows", "local", "test_subworkflow_local.nf"))


def test_subworkflows_create_fail_exists(self):
    """Fail at creating the same subworkflow twice"""
    subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
        self.pipeline_dir, "test_subworkflow2", "@author", False
    )
    subworkflow_create.create()
    with pytest.raises(UserWarning) as excinfo:
        subworkflow_create.create()
    assert "Subworkflow file exists already" in str(excinfo.value)


def test_subworkflows_create_nfcore_modules(self):
    """Create a subworkflow in nf-core/modules clone"""
    subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
        self.nfcore_modules, "test_subworkflow", "@author", force=True
    )
    subworkflow_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "main.nf"))
    assert os.path.exists(
        os.path.join(self.nfcore_modules, "tests", "subworkflows", "nf-core", "test_subworkflow", "main.nf")
    )
