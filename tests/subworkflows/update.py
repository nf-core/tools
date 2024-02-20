import filecmp
import shutil
import tempfile
from pathlib import Path

import yaml

import nf_core.utils
from nf_core.modules.modules_json import ModulesJson
from nf_core.modules.modules_repo import NF_CORE_MODULES_NAME, NF_CORE_MODULES_REMOTE
from nf_core.modules.update import ModuleUpdate
from nf_core.subworkflows.update import SubworkflowUpdate

from ..utils import OLD_SUBWORKFLOWS_SHA


def test_install_and_update(self):
    """Installs a subworkflow in the pipeline and updates it (no change)"""
    self.subworkflow_install.install("bam_stats_samtools")
    update_obj = SubworkflowUpdate(self.pipeline_dir, show_diff=False)

    # Copy the sw files and check that they are unaffected by the update
    tmpdir = tempfile.mkdtemp()
    shutil.rmtree(tmpdir)
    sw_path = Path(self.pipeline_dir, "subworkflows", NF_CORE_MODULES_NAME, "bam_stats_samtools")
    shutil.copytree(sw_path, tmpdir)

    assert update_obj.update("bam_stats_samtools") is True
    assert cmp_component(tmpdir, sw_path) is True


def test_install_at_hash_and_update(self):
    """Installs an old version of a subworkflow in the pipeline and updates it"""
    assert self.subworkflow_install_old.install("fastq_align_bowtie2")
    update_obj = SubworkflowUpdate(self.pipeline_dir, show_diff=False, update_deps=True)
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Copy the sw files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    shutil.rmtree(tmpdir)
    sw_path = Path(self.pipeline_dir, "subworkflows", NF_CORE_MODULES_NAME, "fastq_align_bowtie2")
    shutil.copytree(sw_path, tmpdir)

    assert update_obj.update("fastq_align_bowtie2") is True
    assert cmp_component(tmpdir, sw_path) is False

    # Check that the modules.json is correctly updated
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    # Get the up-to-date git_sha for the sw from the ModulesRepo object
    assert (
        old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
        != mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
    )


def test_install_at_hash_and_update_and_save_diff_to_file(self):
    """Installs an old version of a sw in the pipeline and updates it. Save differences to a file."""
    assert self.subworkflow_install_old.install("fastq_align_bowtie2")
    patch_path = Path(self.pipeline_dir, "fastq_align_bowtie2.patch")
    update_obj = SubworkflowUpdate(self.pipeline_dir, save_diff_fn=patch_path, update_deps=True)

    # Copy the sw files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    shutil.rmtree(tmpdir)
    sw_path = Path(self.pipeline_dir, "subworkflows", NF_CORE_MODULES_NAME, "fastq_align_bowtie2")
    shutil.copytree(sw_path, tmpdir)

    assert update_obj.update("fastq_align_bowtie2") is True
    assert cmp_component(tmpdir, sw_path) is True

    with open(patch_path) as fh:
        line = fh.readline()
        assert line.startswith(
            "Changes in module 'nf-core/fastq_align_bowtie2' between (f3c078809a2513f1c95de14f6633fe1f03572fdb) and"
        )


def test_update_all(self):
    """Updates all subworkflows present in the pipeline"""
    # Install subworkflows fastq_align_bowtie2, bam_sort_stats_samtools, bam_stats_samtools
    self.subworkflow_install.install("fastq_align_bowtie2")
    # Update all subworkflows
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # We must reload the modules.json to get the updated version
    mod_json_obj = ModulesJson(self.pipeline_dir)
    mod_json = mod_json_obj.get_modules_json()
    # Loop through all subworkflows and check that they are updated (according to the modules.json file)
    for sw in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]:
        correct_git_sha = list(update_obj.modules_repo.get_component_git_log(sw, "subworkflows", depth=1))[0]["git_sha"]
        current_git_sha = mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]["git_sha"]
        assert correct_git_sha == current_git_sha


def test_update_with_config_fixed_version(self):
    """Try updating when there are entries in the .nf-core.yml"""
    # Install subworkflow at the latest version
    assert self.subworkflow_install.install("fastq_align_bowtie2")

    # Fix the subworkflow version in the .nf-core.yml to an old version
    update_config = {NF_CORE_MODULES_REMOTE: {NF_CORE_MODULES_NAME: {"fastq_align_bowtie2": OLD_SUBWORKFLOWS_SHA}}}
    config_fn, tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(Path(self.pipeline_dir, config_fn), "w") as f:
        yaml.dump(tools_config, f)

    # Update all subworkflows in the pipeline
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for fastq_align_bowtie2 is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    assert "fastq_align_bowtie2" in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]
    assert (
        "git_sha"
        in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"]
    )
    assert (
        mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
        == OLD_SUBWORKFLOWS_SHA
    )


def test_update_with_config_dont_update(self):
    """Try updating when sw is to be ignored"""
    # Install an old version of fastq_align_bowtie2
    self.subworkflow_install_old.install("fastq_align_bowtie2")

    # Set the fastq_align_bowtie2 field to no update in the .nf-core.yml
    update_config = {NF_CORE_MODULES_REMOTE: {NF_CORE_MODULES_NAME: {"fastq_align_bowtie2": False}}}
    config_fn, tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(Path(self.pipeline_dir, config_fn), "w") as f:
        yaml.dump(tools_config, f)

    # Update all modules in the pipeline
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for fastq_align_bowtie2 is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    assert "fastq_align_bowtie2" in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]
    assert (
        "git_sha"
        in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"]
    )
    assert (
        mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
        == OLD_SUBWORKFLOWS_SHA
    )


def test_update_with_config_fix_all(self):
    """Fix the version of all nf-core subworkflows"""
    # Install subworkflow at the latest version
    assert self.subworkflow_install.install("fastq_align_bowtie2")

    # Fix the version of all nf-core subworkflows in the .nf-core.yml to an old version
    update_config = {NF_CORE_MODULES_REMOTE: OLD_SUBWORKFLOWS_SHA}
    config_fn, tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(Path(self.pipeline_dir, config_fn), "w") as f:
        yaml.dump(tools_config, f)

    # Update fastq_align_bowtie2
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_all=False, update_deps=True, show_diff=False)
    assert update_obj.update("fastq_align_bowtie2") is True

    # Check that the git sha for fastq_align_bowtie2 is correctly downgraded
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    assert (
        "git_sha"
        in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"]
    )
    assert (
        mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
        == OLD_SUBWORKFLOWS_SHA
    )


def test_update_with_config_no_updates(self):
    """Don't update any nf-core subworkflows"""
    # Install an old version of fastq_align_bowtie2
    self.subworkflow_install_old.install("fastq_align_bowtie2")
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Set all repository updates to False
    update_config = {NF_CORE_MODULES_REMOTE: False}
    config_fn, tools_config = nf_core.utils.load_tools_config(self.pipeline_dir)
    tools_config["update"] = update_config
    with open(Path(self.pipeline_dir, config_fn), "w") as f:
        yaml.dump(tools_config, f)

    # Update all subworkflows in the pipeline
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_all=True, show_diff=False)
    assert update_obj.update() is True

    # Check that the git sha for fastq_align_bowtie2 is correctly downgraded and none of the subworkflows has changed
    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    for sw in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]:
        assert "git_sha" in mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]
        assert (
            mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]["git_sha"]
            == old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]["git_sha"]
        )


def test_update_all_linked_components_from_subworkflow(self):
    """Update a subworkflow and all modules and subworkflows used on it"""
    # Install an old version of fastq_align_bowtie2
    self.subworkflow_install_old.install("fastq_align_bowtie2")
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Copy the sw files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    shutil.rmtree(tmpdir)
    subworkflows_path = Path(self.pipeline_dir, "subworkflows", NF_CORE_MODULES_NAME)
    modules_path = Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME)
    shutil.copytree(subworkflows_path, Path(tmpdir, "subworkflows"))
    shutil.copytree(modules_path, Path(tmpdir, "modules"))

    # Update fastq_align_bowtie2 and all modules and subworkflows used by that
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_deps=True, show_diff=False)
    assert update_obj.update("fastq_align_bowtie2") is True

    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    # Loop through all modules and subworkflows used in fastq_align_bowtie2
    # check that they are updated (according to the modules.json file)
    for sw in ["fastq_align_bowtie2", "bam_sort_stats_samtools", "bam_stats_samtools"]:
        assert (
            old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]["git_sha"]
            != mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME][sw]["git_sha"]
        )
    for mod in [
        "bowtie2/align",
        "samtools/index",
        "samtools/sort",
        "samtools/flagstat",
        "samtools/idxstats",
        "samtools/stats",
    ]:
        assert (
            old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME][mod]["git_sha"]
            != mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME][mod]["git_sha"]
        )
    # Check that the subworkflow files are updated
    assert (
        cmp_component(
            Path(tmpdir, "subworkflows", "fastq_align_bowtie2"), Path(subworkflows_path, "fastq_align_bowtie2")
        )
        is False
    )


def test_update_all_subworkflows_from_module(self):
    """Update a module and all subworkflows that use this module"""
    # Install an old version of fastq_align_bowtie2 and thus all modules used by it (bowtie2/align)
    self.subworkflow_install_old.install("fastq_align_bowtie2")
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Copy the sw files and check that they are affected by the update
    tmpdir = tempfile.mkdtemp()
    shutil.rmtree(tmpdir)
    sw_path = Path(self.pipeline_dir, "subworkflows", NF_CORE_MODULES_NAME, "fastq_align_bowtie2")
    shutil.copytree(sw_path, Path(tmpdir, "fastq_align_bowtie2"))

    # Update bowtie2/align and all subworkflows using it
    update_obj = ModuleUpdate(self.pipeline_dir, update_deps=True, show_diff=False)
    assert update_obj.update("bowtie2/align") is True

    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()
    # Check that bowtie2/align and fastq_align_bowtie2 are updated
    assert (
        old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
        != mod_json["repos"][NF_CORE_MODULES_REMOTE]["subworkflows"][NF_CORE_MODULES_NAME]["fastq_align_bowtie2"][
            "git_sha"
        ]
    )
    assert cmp_component(Path(tmpdir, "fastq_align_bowtie2"), sw_path) is False
    assert (
        old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]["bowtie2/align"]["git_sha"]
        != mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]["bowtie2/align"]["git_sha"]
    )


def test_update_change_of_included_modules(self):
    """Update a subworkflow which has a module change in the new version."""
    # Install an old version of vcf_annotate_ensemblvep with tabix/bgziptabix and without tabix/tabix
    self.subworkflow_install_module_change.install("vcf_annotate_ensemblvep")
    old_mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Check that tabix/bgziptabix is there
    assert "tabix/bgziptabix" in old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "tabix/bgziptabix").is_dir()
    # Check that tabix/tabix is not there
    assert "tabix/tabix" not in old_mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert not Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "tabix/tabix").is_dir()

    # Update vcf_annotate_ensemblvep without tabix/bgziptabix and with tabix/tabix
    update_obj = SubworkflowUpdate(self.pipeline_dir, update_deps=True, show_diff=False)
    assert update_obj.update("vcf_annotate_ensemblvep") is True

    mod_json = ModulesJson(self.pipeline_dir).get_modules_json()

    # Check that tabix/bgziptabix is not there
    assert "tabix/bgziptabix" not in mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert not Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "tabix/bgziptabix").is_dir()
    # Check that tabix/tabix is there
    assert "tabix/tabix" in mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "tabix/tabix").is_dir()
    # Check that ensemblevep is not there but instead we have ensemblevep/vep (due to a file re-naming)
    assert "ensemblvep" not in mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert "ensemblvep/vep" in mod_json["repos"][NF_CORE_MODULES_REMOTE]["modules"][NF_CORE_MODULES_NAME]
    assert Path(self.pipeline_dir, "modules", NF_CORE_MODULES_NAME, "ensemblvep/vep").is_dir()


def cmp_component(dir1, dir2):
    """Compare two versions of the same component"""
    files = ["main.nf", "meta.yml"]
    return all(filecmp.cmp(Path(dir1, f), Path(dir2, f), shallow=False) for f in files)
