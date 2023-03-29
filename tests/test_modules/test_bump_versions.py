import os
import re

import pytest

import nf_core.modules
from nf_core.modules.modules_utils import ModuleException


def test_modules_bump_versions_single_module(local_modules_repo):
    """Test updating a single module"""
    # Change the bpipe/test version to an older version
    print(local_modules_repo.__dir__())
    main_nf_path = os.path.join(local_modules_repo, "modules", "nf-core", "bpipe", "test", "main.nf")
    with open(main_nf_path, "r") as fh:
        content = fh.read()
    new_content = re.sub(r"bioconda::star=\d.\d.\d\D?", r"bioconda::star=2.6.1d", content)
    with open(main_nf_path, "w") as fh:
        fh.write(new_content)
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=local_modules_repo)
    version_bumper.bump_versions(module="bpipe/test")
    assert len(version_bumper.failed) == 0


def test_modules_bump_versions_all_modules(local_modules_repo):
    """Test updating all modules"""
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=local_modules_repo)
    version_bumper.bump_versions(all_modules=True)
    assert len(version_bumper.failed) == 0


def test_modules_bump_versions_fail(local_modules_repo):
    """Fail updating a module with wrong name"""
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=local_modules_repo)
    with pytest.raises(ModuleException) as excinfo:
        version_bumper.bump_versions(module="no/module")
    assert "Could not find the specified module:" in str(excinfo.value)


def test_modules_bump_versions_fail_unknown_version(local_modules_repo):
    """Fail because of an unknown version"""
    # Change the bpipe/test version to an older version
    main_nf_path = os.path.join(local_modules_repo, "modules", "nf-core", "bpipe", "test", "main.nf")
    with open(main_nf_path, "r") as fh:
        content = fh.read()
    new_content = re.sub(r"bioconda::bpipe=\d.\d.\d\D?", r"bioconda::bpipe=xxx", content)
    with open(main_nf_path, "w") as fh:
        fh.write(new_content)
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=local_modules_repo)
    version_bumper.bump_versions(module="bpipe/test")
    assert "Conda package had unknown version" in version_bumper.failed[0][0]
