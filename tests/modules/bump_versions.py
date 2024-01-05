import os
import re

import pytest

import nf_core.modules
from nf_core.modules.modules_utils import ModuleExceptionError


def test_modules_bump_versions_single_module(self):
    """Test updating a single module"""
    # Change the bpipe/test version to an older version
    env_yml_path = os.path.join(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")
    with open(env_yml_path) as fh:
        content = fh.read()
    new_content = re.sub(r"bioconda::star=\d.\d.\d\D?", r"bioconda::star=2.6.1d", content)
    with open(env_yml_path, "w") as fh:
        fh.write(new_content)
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
    version_bumper.bump_versions(module="bpipe/test")
    assert len(version_bumper.failed) == 0


def test_modules_bump_versions_all_modules(self):
    """Test updating all modules"""
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
    version_bumper.bump_versions(all_modules=True)
    assert len(version_bumper.failed) == 0


def test_modules_bump_versions_fail(self):
    """Fail updating a module with wrong name"""
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
    with pytest.raises(ModuleExceptionError) as excinfo:
        version_bumper.bump_versions(module="no/module")
    assert "Could not find the specified module:" in str(excinfo.value)


def test_modules_bump_versions_fail_unknown_version(self):
    """Fail because of an unknown version"""
    # Change the bpipe/test version to an older version
    env_yml_path = os.path.join(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")
    with open(env_yml_path) as fh:
        content = fh.read()
    new_content = re.sub(r"bioconda::bpipe=\d.\d.\d\D?", r"bioconda::bpipe=xxx", content)
    with open(env_yml_path, "w") as fh:
        fh.write(new_content)
    version_bumper = nf_core.modules.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
    version_bumper.bump_versions(module="bpipe/test")
    assert "Conda package had unknown version" in version_bumper.failed[0][0]
