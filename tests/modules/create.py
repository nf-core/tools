import filecmp
import os

import pytest

import nf_core.modules


def test_modules_create_succeed(self):
    """Succeed at creating the TrimGalore! module"""
    module_create = nf_core.modules.ModuleCreate(
        self.pipeline_dir, "trimgalore", "@author", "process_low", True, True, conda_name="trim-galore"
    )
    module_create.create()
    assert os.path.exists(os.path.join(self.pipeline_dir, "modules", "local", "trimgalore.nf"))


def test_modules_create_fail_exists(self):
    """Fail at creating the same module twice"""
    module_create = nf_core.modules.ModuleCreate(
        self.pipeline_dir, "trimgalore", "@author", "process_low", False, False, conda_name="trim-galore"
    )
    module_create.create()
    with pytest.raises(UserWarning) as excinfo:
        module_create.create()
    assert "Module file exists already" in str(excinfo.value)


def test_modules_create_nfcore_modules(self):
    """Create a module in nf-core/modules clone"""
    module_create = nf_core.modules.ModuleCreate(self.nfcore_modules, "fastqc", "@author", "process_low", False, False)
    module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "fastqc", "main.nf"))
    assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "modules", "fastqc", "main.nf"))


def test_modules_create_nfcore_modules_subtool(self):
    """Create a tool/subtool module in a nf-core/modules clone"""
    module_create = nf_core.modules.ModuleCreate(
        self.nfcore_modules, "star/index", "@author", "process_medium", False, False
    )
    module_create.create()
    assert os.path.exists(os.path.join(self.nfcore_modules, "modules", "star", "index", "main.nf"))
    assert os.path.exists(os.path.join(self.nfcore_modules, "tests", "modules", "star", "index", "main.nf"))


def test_modules_create_maintain_pytestyml(self):
    """Create a new tool/subtool and check if pytest_modules.yml has the proper structure"""
    yml = (
        "abacas:\n"
        "- modules/abacas/**\n"
        "- tests/modules/abacas/**\n\n"
        "subworkflows/bam_stats_samtools: &subworkflows_bam_stats_samtools\n"
        "- subworkflows/nf-core/bam_stats_samtools/**\n"
        "- tests/subworkflows/nf-core/bam_stats_samtools/**\n\n"
        "~anchors:\n"
        "- *subworkflows_bam_stats_samtools\n"
    )

    new_yml = (
        "abacas:\n"
        "- modules/abacas/**\n"
        "- tests/modules/abacas/**\n\n"
        "fastqc:\n"
        "- modules/fastqc/**\n"
        "- tests/modules/fastqc/**\n\n"
        "subworkflows/bam_stats_samtools: &subworkflows_bam_stats_samtools\n"
        "- subworkflows/nf-core/bam_stats_samtools/**\n"
        "- tests/subworkflows/nf-core/bam_stats_samtools/**\n\n"
        "~anchors:\n"
        "- *subworkflows_bam_stats_samtools\n"
    )

    with open(os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules.yml"), "w") as fh:
        fh.write(yml)

    with open(os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules_updated.yml"), "w") as fh:
        fh.write(new_yml)

    module_create = nf_core.modules.ModuleCreate(
        self.nfcore_modules, "fastqc", "@author", "process_medium", False, False
    )
    module_create.create()

    with open(os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules.yml"), "r") as fh:
        print(fh.read())
    with open(os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules_updated.yml"), "r") as fh:
        print(fh.read())

    assert filecmp.cmp(
        os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules.yml"),
        os.path.join(self.nfcore_modules, "tests", "config", "pytest_modules_updated.yml"),
    )
