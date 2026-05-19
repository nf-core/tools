from pathlib import Path

import pytest

import nf_core.subworkflows

from ..test_subworkflows import TestSubworkflows


class TestSubworkflowsCreate(TestSubworkflows):
    def test_subworkflows_create_succeed(self):
        """Succeed at creating a subworkflow from the template inside a pipeline"""
        subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
            self.pipeline_dir, "test_subworkflow_local", "@author", True
        )
        subworkflow_create.create()
        assert Path(self.pipeline_dir, "subworkflows", "local", "test_subworkflow_local/main.nf").exists()

    def test_subworkflows_create_fail_exists(self):
        """Fail at creating the same subworkflow twice"""
        subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
            self.pipeline_dir, "test_subworkflow2", "@author", False
        )
        subworkflow_create.create()
        with pytest.raises(UserWarning) as excinfo:
            subworkflow_create.create()
        assert "subworkflow directory exists" in str(excinfo.value)

    def test_subworkflows_create_nfcore_modules(self):
        """Create a subworkflow in nf-core/modules clone"""
        subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
            self.nfcore_modules, "test_subworkflow", "@author", force=True
        )
        subworkflow_create.create()
        assert Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "main.nf").exists()

        assert Path(
            self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test"
        ).exists()
