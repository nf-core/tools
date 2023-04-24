import os

import pytest

from nf_core.modules.modules_json import ModulesJson
from nf_core.subworkflows.install import SubworkflowInstall

from ..utils import (
    GITLAB_BRANCH_TEST_BRANCH,
    GITLAB_REPO,
    GITLAB_SUBWORKFLOWS_BRANCH,
    GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH,
    GITLAB_URL,
    with_temporary_folder,
)


def test_subworkflow_install_nopipeline(self):
    """Test installing a subworkflow - no pipeline given"""
    self.subworkflow_install.dir = None
    assert self.subworkflow_install.install("foo") is False


@with_temporary_folder
def test_subworkflows_install_emptypipeline(self, tmpdir):
    """Test installing a subworkflow - empty dir given"""
    os.mkdir(os.path.join(tmpdir, "nf-core-pipe"))
    self.subworkflow_install.dir = os.path.join(tmpdir, "nf-core-pipe")
    with pytest.raises(UserWarning) as excinfo:
        self.subworkflow_install.install("foo")
    assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)


def test_subworkflows_install_nosubworkflow(self):
    """Test installing a subworkflow - unrecognised subworkflow given"""
    assert self.subworkflow_install.install("foo") is False


def test_subworkflows_install_bam_sort_stats_samtools(self):
    """Test installing a subworkflow - bam_sort_stats_samtools"""
    assert self.subworkflow_install.install("bam_sort_stats_samtools") is not False
    subworkflow_path = os.path.join(self.subworkflow_install.dir, "subworkflows", "nf-core", "bam_sort_stats_samtools")
    sub_subworkflow_path = os.path.join(self.subworkflow_install.dir, "subworkflows", "nf-core", "bam_stats_samtools")
    samtools_index_path = os.path.join(self.subworkflow_install.dir, "modules", "nf-core", "samtools", "index")
    samtools_sort_path = os.path.join(self.subworkflow_install.dir, "modules", "nf-core", "samtools", "sort")
    samtools_stats_path = os.path.join(self.subworkflow_install.dir, "modules", "nf-core", "samtools", "stats")
    samtools_idxstats_path = os.path.join(self.subworkflow_install.dir, "modules", "nf-core", "samtools", "idxstats")
    samtools_flagstat_path = os.path.join(self.subworkflow_install.dir, "modules", "nf-core", "samtools", "flagstat")
    assert os.path.exists(subworkflow_path)
    assert os.path.exists(sub_subworkflow_path)
    assert os.path.exists(samtools_index_path)
    assert os.path.exists(samtools_sort_path)
    assert os.path.exists(samtools_stats_path)
    assert os.path.exists(samtools_idxstats_path)
    assert os.path.exists(samtools_flagstat_path)


def test_subworkflows_install_bam_sort_stats_samtools_twice(self):
    """Test installing a subworkflow - bam_sort_stats_samtools already there"""
    self.subworkflow_install.install("bam_sort_stats_samtools")
    assert self.subworkflow_install.install("bam_sort_stats_samtools") is False


def test_subworkflows_install_from_gitlab(self):
    """Test installing a subworkflow from GitLab"""
    assert self.subworkflow_install_gitlab.install("bam_stats_samtools") is True
    # Verify that the branch entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    assert (
        modules_json.get_component_branch(self.component_type, "bam_stats_samtools", GITLAB_URL, GITLAB_REPO)
        == GITLAB_SUBWORKFLOWS_BRANCH
    )


def test_subworkflows_install_different_branch_fail(self):
    """Test installing a subworkflow from a different branch"""
    install_obj = SubworkflowInstall(self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_BRANCH_TEST_BRANCH)
    # The bam_stats_samtools subworkflow does not exists in the branch-test branch
    assert install_obj.install("bam_stats_samtools") is False


def test_subworkflows_install_tracking(self):
    """Test installing a subworkflow and finding the correct entries in installed_by section of modules.json"""
    self.subworkflow_install.install("bam_sort_stats_samtools")

    # Verify that the installed_by entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    mod_json = modules_json.get_modules_json()
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"][
        "bam_sort_stats_samtools"
    ]["installed_by"] == ["subworkflows"]
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"]["bam_stats_samtools"][
        "installed_by"
    ] == ["bam_sort_stats_samtools"]
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]["samtools/stats"][
        "installed_by"
    ] == ["bam_stats_samtools"]
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["modules"]["nf-core"]["samtools/sort"][
        "installed_by"
    ] == ["bam_sort_stats_samtools"]

    # Clean directory
    self.subworkflow_remove.remove("bam_sort_stats_samtools")


def test_subworkflows_install_tracking_added_already_installed(self):
    """Test installing a subworkflow and finding the correct entries in installed_by section of modules.json"""
    self.subworkflow_install.install("bam_sort_stats_samtools")
    self.subworkflow_install.install("bam_stats_samtools")

    # Verify that the installed_by entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    mod_json = modules_json.get_modules_json()
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"][
        "bam_sort_stats_samtools"
    ]["installed_by"] == ["subworkflows"]
    assert sorted(
        mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"]["bam_stats_samtools"][
            "installed_by"
        ]
    ) == sorted(["bam_sort_stats_samtools", "subworkflows"])

    # Clean directory
    self.subworkflow_remove.remove("bam_sort_stats_samtools")
    self.subworkflow_remove.remove("bam_stats_samtools")


def test_subworkflows_install_tracking_added_super_subworkflow(self):
    """Test installing a subworkflow and finding the correct entries in installed_by section of modules.json"""
    self.subworkflow_install.install("bam_stats_samtools")
    self.subworkflow_install.install("bam_sort_stats_samtools")

    # Verify that the installed_by entry was added correctly
    modules_json = ModulesJson(self.pipeline_dir)
    mod_json = modules_json.get_modules_json()
    assert mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"][
        "bam_sort_stats_samtools"
    ]["installed_by"] == ["subworkflows"]
    assert sorted(
        mod_json["repos"]["https://github.com/nf-core/modules.git"]["subworkflows"]["nf-core"]["bam_stats_samtools"][
            "installed_by"
        ]
    ) == sorted(["subworkflows", "bam_sort_stats_samtools"])


def test_subworkflows_install_alternate_remote(self):
    """Test installing a module from a different remote with the same organization path"""
    install_obj = SubworkflowInstall(
        self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_SUBWORKFLOWS_ORG_PATH_BRANCH
    )
    # Install a subworkflow from GitLab which is also installed from GitHub with the same org_path
    with pytest.raises(Exception) as excinfo:
        install_obj.install("fastqc")
        assert "Could not find a 'main.nf' or 'nextflow.config' file" in str(excinfo.value)
