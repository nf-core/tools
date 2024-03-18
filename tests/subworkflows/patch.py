import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import nf_core.components.components_command
import nf_core.subworkflows

from ..utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_URL,
)

# TODO: #Change this for the correct SUCCEED_SHA
SUCCEED_SHA = "????"

"""
Test the 'nf-core subworkflows patch' command
"""


def setup_patch(self, pipeline_dir, modify_subworkflow):
    # Install the subworkflow bam_sort_stats_samtools
    subworkflow_path = os.path.join(self.subworkflow_install.dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")

    if modify_subworkflow:
        # Modify the subworkflow
        subworkflow_path = Path(pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")
        modify_subworkflow(subworkflow_path / "main.nf")


def modify_subworkflow(path):
    """Modify a file to test patch creation"""
    with open(path) as fh:
        lines = fh.readlines()
    # We want a patch file that looks something like:
    # -    ch_fasta // channel: [ val(meta), path(fasta) ]
    for line_index in range(len(lines)):
        if lines[line_index] == "    ch_fasta // channel: [ val(meta), path(fasta) ]\n":
            to_pop = line_index
    lines.pop(to_pop)
    with open(path, "w") as fh:
        fh.writelines(lines)


def test_create_patch_no_change(self):
    """Test creating a patch when there is a change to the module"""
    setup_patch(self.pipeline_dir, False)

    # Try creating a patch file
    patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_BRANCH_TEST_BRANCH)
    with pytest.raises(UserWarning):
        patch_obj.patch("bam_sort_stats_samtools")

    subworkflow_path = Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")

    # Check that no patch file has been added to the directory
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml"}


def test_create_patch_change(self):
    """Test creating a patch when there is no change to the subworkflow"""
    setup_patch(self.pipeline_dir, True)

    # Try creating a patch file
    patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_BRANCH_TEST_BRANCH)
    patch_obj.patch("bam_sort_stats_samtools")

    subworkflow_path = Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")

    patch_fn = f"{'-'.join('bam_sort_stats_samtools')}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check that the correct lines are in the patch file
    with open(subworkflow_path / patch_fn) as fh:
        patch_lines = fh.readlines()
    subworkflow_relpath = subworkflow_path.relative_to(self.pipeline_dir)
    assert f"--- {subworkflow_relpath / 'main.nf'}\n" in patch_lines, subworkflow_relpath / "main.nf"
    assert f"+++ {subworkflow_relpath / 'main.nf'}\n" in patch_lines
    assert "-    ch_fasta // channel: [ val(meta), path(fasta) ]" in patch_lines


def test_create_patch_try_apply_successful(self):
    """Test creating a patch file and applying it to a new version of the the files"""
    setup_patch(self.pipeline_dir, True)
    subworkflow_relpath = Path("subworkflows", "nf-core", "bam_sort_stats_samtools")
    subworkflow_path = Path(self.pipeline_dir, subworkflow_relpath)

    # Try creating a patch file
    patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_BRANCH_TEST_BRANCH)
    patch_obj.patch("bam_sort_stats_samtools")

    patch_fn = f"{'-'.join('bam_sort_stats_samtools')}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", patch_fn}

    update_obj = nf_core.subworkflows.SubworkflowUpdate(
        self.pipeline_dir, sha=SUCCEED_SHA, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH
    )

    # Install the new files
    install_dir = Path(tempfile.mkdtemp())
    update_obj.install_component_files("bam_sort_stats_samtools", SUCCEED_SHA, update_obj.modules_repo, install_dir)

    # Try applying the patch
    subworkflow_install_dir = install_dir / "bam_sort_stats_samtools"
    patch_relpath = subworkflow_relpath / patch_fn
    assert (
        update_obj.try_apply_patch(
            "bam_sort_stats_samtools", "nf-core", patch_relpath, subworkflow_path, subworkflow_install_dir
        )
        is True
    )

    # Move the files from the temporary directory
    update_obj.move_files_from_tmp_dir("bam_sort_stats_samtools", install_dir, "nf-core", SUCCEED_SHA)

    # Check that a patch file with the correct name has been created
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", patch_fn}

    # Check that the correct lines are in the patch file
    with open(subworkflow_path / patch_fn) as fh:
        patch_lines = fh.readlines()
    subworkflow_relpath = subworkflow_path.relative_to(self.pipeline_dir)
    assert f"--- {subworkflow_relpath / 'main.nf'}\n" in patch_lines, subworkflow_relpath / "main.nf"
    assert f"+++ {subworkflow_relpath / 'main.nf'}\n" in patch_lines
    assert "-    ch_fasta // channel: [ val(meta), path(fasta) ]" in patch_lines

    # Check that 'main.nf' is updated correctly
    with open(subworkflow_path / "main.nf") as fh:
        main_nf_lines = fh.readlines()
    # These lines should have been removed by the patch
    assert "    ch_fasta // channel: [ val(meta), path(fasta) ]\n" not in main_nf_lines


def test_create_patch_try_apply_failed(self):
    """Test creating a patch file and applying it to a new version of the the files"""
    setup_patch(self.pipeline_dir, True)
    subworkflow_relpath = Path("subworkflows", "nf-core", "bam_sort_stats_samtools")
    subworkflow_path = Path(self.pipeline_dir, subworkflow_relpath)

    # Try creating a patch file
    patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_BRANCH_TEST_BRANCH)
    patch_obj.patch("bam_sort_stats_samtools")

    patch_fn = f"{'-'.join('bam_sort_stats_samtools')}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", patch_fn}

    update_obj = nf_core.subworkflows.SubworkflowUpdate(
        self.pipeline_dir, sha=SUCCEED_SHA, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH
    )

    # Install the new files
    install_dir = Path(tempfile.mkdtemp())
    update_obj.install_component_files("bam_sort_stats_samtools", SUCCEED_SHA, update_obj.modules_repo, install_dir)

    # Try applying the patch
    subworkflow_install_dir = install_dir / "bam_sort_stats_samtools"
    patch_relpath = subworkflow_relpath / patch_fn
    assert (
        update_obj.try_apply_patch(
            "bam_sort_stats_samtools", "nf-core", patch_relpath, subworkflow_path, subworkflow_install_dir
        )
        is False
    )


# TODO: create those two missing tests
def test_create_patch_update_success(self):
    """Test creating a patch file and updating a subworkflow when there is a diff conflict"""


def test_create_patch_update_fail(self):
    """
    Test creating a patch file and the updating the subworkflow

    Should have the same effect as 'test_create_patch_try_apply_successful'
    but uses higher level api
    """


def test_remove_patch(self):
    """Test creating a patch when there is no change to the subworkflow"""
    setup_patch(self.pipeline_dir, True)

    # Try creating a patch file
    patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_BRANCH_TEST_BRANCH)
    patch_obj.patch("bam_sort_stats_samtools")

    subworkflow_path = Path(self.pipeline_dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")

    patch_fn = f"{'-'.join('bam_sort_stats_samtools')}.diff"
    # Check that a patch file with the correct name has been created
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", patch_fn}

    with mock.patch.object(nf_core.create.questionary, "confirm") as mock_questionary:
        mock_questionary.unsafe_ask.return_value = True
        patch_obj.remove("bam_sort_stats_samtools")
    # Check that the diff file has been removed
    assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml"}
