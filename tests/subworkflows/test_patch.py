import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

import nf_core.components.components_command
import nf_core.components.patch
import nf_core.subworkflows

from ..test_subworkflows import TestSubworkflows
from ..utils import GITLAB_REPO, GITLAB_SUBWORKFLOWS_BRANCH, GITLAB_URL

OLD_SHA = "dbb12457e32d3da8eea7dc4ae096201fff4747c5"
SUCCEED_SHA = "0a33e6a0d730ad22a0ec9f7f9a7540af6e943221"
FAIL_SHA = "b6e5e8739de9a1a0c4f85267144e43dbaf8f1461"


class TestSubworkflowsPatch(TestSubworkflows):
    """
    Test the 'nf-core subworkflows patch' command
    """

    def modify_main_nf(self, path):
        """Modify a file to test patch creation"""
        with open(path) as fh:
            lines = fh.readlines()
        # We want a patch file that looks something like:
        # -    ch_fasta // channel: [ fasta ]
        for line_index in range(len(lines)):
            if lines[line_index] == "    ch_fasta // channel: [ fasta ]\n":
                to_pop = line_index
        lines.pop(to_pop)
        with open(path, "w") as fh:
            fh.writelines(lines)

    def setup_patch(self, pipeline_dir, modify_subworkflow):
        # Install the subworkflow bam_sort_stats_samtools
        install_obj = nf_core.subworkflows.SubworkflowInstall(
            pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=GITLAB_SUBWORKFLOWS_BRANCH,
            sha=OLD_SHA,
        )

        # Install the module
        install_obj.install("bam_sort_stats_samtools")

        if modify_subworkflow:
            # Modify the subworkflow
            subworkflow_path = Path(pipeline_dir, "subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")
            self.modify_main_nf(subworkflow_path / "main.nf")

    def test_create_patch_no_change(self):
        """Test creating a patch when there is a change to the module"""
        self.setup_patch(self.pipeline_dir, False)

        # Try creating a patch file
        patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_SUBWORKFLOWS_BRANCH)
        with pytest.raises(UserWarning):
            patch_obj.patch("bam_sort_stats_samtools")

        subworkflow_path = Path(self.pipeline_dir, "subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")

        # Check that no patch file has been added to the directory
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml"}

    def test_create_patch_change(self):
        """Test creating a patch when there is no change to the subworkflow"""
        self.setup_patch(self.pipeline_dir, True)

        # Try creating a patch file
        patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_SUBWORKFLOWS_BRANCH)
        patch_obj.patch("bam_sort_stats_samtools")

        subworkflow_path = Path(self.pipeline_dir, "subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")

        # Check that a patch file with the correct name has been created
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", "bam_sort_stats_samtools.diff"}

        # Check that the correct lines are in the patch file
        with open(subworkflow_path / "bam_sort_stats_samtools.diff") as fh:
            patch_lines = fh.readlines()
        print(patch_lines)
        subworkflow_relpath = subworkflow_path.relative_to(self.pipeline_dir)
        assert f"--- {subworkflow_relpath / 'main.nf'}\n" in patch_lines, subworkflow_relpath / "main.nf"
        assert f"+++ {subworkflow_relpath / 'main.nf'}\n" in patch_lines
        assert "-    ch_fasta // channel: [ fasta ]\n" in patch_lines

    def test_create_patch_try_apply_successful(self):
        """Test creating a patch file and applying it to a new version of the the files"""
        self.setup_patch(self.pipeline_dir, True)
        subworkflow_relpath = Path("subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")
        subworkflow_path = Path(self.pipeline_dir, subworkflow_relpath)

        # Try creating a patch file
        patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_SUBWORKFLOWS_BRANCH)
        patch_obj.patch("bam_sort_stats_samtools")

        # Check that a patch file with the correct name has been created
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", "bam_sort_stats_samtools.diff"}

        update_obj = nf_core.subworkflows.SubworkflowUpdate(
            self.pipeline_dir, sha=OLD_SHA, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
        )

        # Install the new files
        install_dir = Path(tempfile.mkdtemp())
        update_obj.install_component_files("bam_sort_stats_samtools", OLD_SHA, update_obj.modules_repo, install_dir)

        # Try applying the patch
        subworkflow_install_dir = install_dir / "bam_sort_stats_samtools"
        patch_relpath = subworkflow_relpath / "bam_sort_stats_samtools.diff"
        assert (
            update_obj.try_apply_patch(
                "bam_sort_stats_samtools", GITLAB_REPO, patch_relpath, subworkflow_path, subworkflow_install_dir
            )
            is True
        )

        # Move the files from the temporary directory
        update_obj.move_files_from_tmp_dir("bam_sort_stats_samtools", install_dir, GITLAB_REPO, OLD_SHA)

        # Check that a patch file with the correct name has been created
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", "bam_sort_stats_samtools.diff"}

        # Check that the correct lines are in the patch file
        with open(subworkflow_path / "bam_sort_stats_samtools.diff") as fh:
            patch_lines = fh.readlines()
        subworkflow_relpath = subworkflow_path.relative_to(self.pipeline_dir)
        assert f"--- {subworkflow_relpath / 'main.nf'}\n" in patch_lines, subworkflow_relpath / "main.nf"
        assert f"+++ {subworkflow_relpath / 'main.nf'}\n" in patch_lines
        assert "-    ch_fasta // channel: [ fasta ]\n" in patch_lines

        # Check that 'main.nf' is updated correctly
        with open(subworkflow_path / "main.nf") as fh:
            main_nf_lines = fh.readlines()
        # These lines should have been removed by the patch
        assert "-    ch_fasta // channel: [ fasta ]\n" not in main_nf_lines

    def test_create_patch_try_apply_failed(self):
        """Test creating a patch file and applying it to a new version of the the files"""
        self.setup_patch(self.pipeline_dir, True)
        subworkflow_relpath = Path("subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")
        subworkflow_path = Path(self.pipeline_dir, subworkflow_relpath)

        # Try creating a patch file
        patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_SUBWORKFLOWS_BRANCH)
        patch_obj.patch("bam_sort_stats_samtools")

        # Check that a patch file with the correct name has been created
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", "bam_sort_stats_samtools.diff"}

        update_obj = nf_core.subworkflows.SubworkflowUpdate(
            self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_BRANCH
        )

        # Install the new files
        install_dir = Path(tempfile.mkdtemp())
        update_obj.install_component_files("bam_sort_stats_samtools", FAIL_SHA, update_obj.modules_repo, install_dir)

        # Try applying the patch
        subworkflow_install_dir = install_dir / "bam_sort_stats_samtools"
        patch_relpath = subworkflow_relpath / "bam_sort_stats_samtools.diff"
        assert (
            update_obj.try_apply_patch(
                "bam_sort_stats_samtools", GITLAB_REPO, patch_relpath, subworkflow_path, subworkflow_install_dir
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
        self.setup_patch(self.pipeline_dir, True)

        # Try creating a patch file
        patch_obj = nf_core.subworkflows.SubworkflowPatch(self.pipeline_dir, GITLAB_URL, GITLAB_SUBWORKFLOWS_BRANCH)
        patch_obj.patch("bam_sort_stats_samtools")

        subworkflow_path = Path(self.pipeline_dir, "subworkflows", GITLAB_REPO, "bam_sort_stats_samtools")

        # Check that a patch file with the correct name has been created
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml", "bam_sort_stats_samtools.diff"}

        with mock.patch.object(nf_core.components.patch.questionary, "confirm") as mock_questionary:
            mock_questionary.unsafe_ask.return_value = True
            patch_obj.remove("bam_sort_stats_samtools")
        # Check that the diff file has been removed
        assert set(os.listdir(subworkflow_path)) == {"main.nf", "meta.yml"}
