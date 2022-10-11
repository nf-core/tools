from rich.console import Console

import nf_core.modules

from ..utils import GITLAB_DEFAULT_BRANCH, GITLAB_URL


def test_subworkflows_list_remote(self):
    """Test listing available subworkflows"""
    swfs_list = nf_core.subworkflows.SubworkflowList(None, remote=True)
    listed_swfs = swfs_list.list_subworkflows()
    console = Console(record=True)
    console.print(listed_swfs)
    output = console.export_text()
    assert "bam_sort_samtools" in output


# def test_subworkflows_list_remote_gitlab(self):
#     """Test listing the subworkflows in the remote gitlab repo"""
#     swfs_list = nf_core.subworkflows.SubworkflowList(None, remote=True, remote_url=GITLAB_URL, branch=GITLAB_DEFAULT_BRANCH)
#     listed_swfs = swfs_list.list_subworkflows()
#     print(f"listed subworkflows are {listed_swfs}")
#     console = Console(record=True)
#     console.print(listed_swfs)
#     output = console.export_text()
#     assert "bam_sort_samtools" in output


def test_subworkflows_install_and_list_pipeline(self):
    """Test listing locally installed subworkflows"""
    self.swfs_install.install("align_bowtie2")
    swfs_list = nf_core.subworkflows.SubworkflowList(self.pipeline_dir, remote=False)
    listed_swfs = swfs_list.list_subworkflows()
    console = Console(record=True)
    console.print(listed_swfs)
    output = console.export_text()
    assert "align_bowtie2" in output


# def test_subworkflows_install_gitlab_and_list_pipeline(self):
#     """Test listing locally installed subworkflows"""
#     self.swfs_install_gitlab.install("bam_sort_samtools")
#     swfs_list = nf_core.subworkflows.SubworkflowList(self.pipeline_dir, remote=False)
#     listed_swfs = swfs_list.list_subworkflows()
#     console = Console(record=True)
#     console.print(listed_swfs)
#     output = console.export_text()
#     assert "bam_sort_samtools" in output
