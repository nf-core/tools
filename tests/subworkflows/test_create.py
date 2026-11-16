from pathlib import Path

import pytest

import nf_core.subworkflows
from tests.utils import NF_CORE_LICENSE_HEADER

from ..test_subworkflows import TestSubworkflows, create_modules_repo_dummy


def test_subworkflows_create_other_org_no_license_header(tmp_path):
    """Create a subworkflow in a modules repo with a non-nf-core org_path, without the nf-core license header"""
    nfcore_modules = create_modules_repo_dummy(tmp_path)
    Path(nfcore_modules, ".nf-core.yml").write_text("repository_type: modules\norg_path: myorg\n")
    nf_core.subworkflows.SubworkflowCreate(nfcore_modules, "test_subworkflow", "@author").create()
    main_nf = Path(nfcore_modules, "subworkflows", "myorg", "test_subworkflow", "main.nf").read_text()
    assert NF_CORE_LICENSE_HEADER not in main_nf


class TestSubworkflowsCreate(TestSubworkflows):
    def test_subworkflows_create_succeed(self):
        """Succeed at creating a subworkflow from the template inside a pipeline"""
        subworkflow_create = nf_core.subworkflows.SubworkflowCreate(
            self.pipeline_dir, "test_subworkflow_local", "@author", True
        )
        subworkflow_create.create()
        subworkflow_dir = Path(self.pipeline_dir, "subworkflows", "local", "test_subworkflow_local")
        assert Path(subworkflow_dir, "main.nf").exists()
        assert NF_CORE_LICENSE_HEADER not in Path(subworkflow_dir, "main.nf").read_text()
        assert 'tag "subworkflows_local"' in Path(subworkflow_dir, "tests", "main.nf.test").read_text()

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
        main_nf = Path(self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "main.nf").read_text()
        assert main_nf.startswith(NF_CORE_LICENSE_HEADER)

        assert Path(
            self.nfcore_modules, "subworkflows", "nf-core", "test_subworkflow", "tests", "main.nf.test"
        ).exists()
