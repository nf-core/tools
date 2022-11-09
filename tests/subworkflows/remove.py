from pathlib import Path


def test_subworkflows_remove_uninstalled_subworkflow(self):
    """Test removing subworkflow without installing it"""
    assert self.subworkflow_remove.remove("bam_sort_stats_samtools") is False


def test_subworkflows_remove_subworkflow(self):
    """Test removing subworkflow and all it's dependencies after installing it"""
    self.subworkflow_install.install("bam_sort_stats_samtools")

    subworkflow_path = Path(self.subworkflow_install.dir, "modules", "nf-core", "subworkflows")
    bam_sort_stats_samtools_path = Path(subworkflow_path, "bam_sort_stats_samtools")
    bam_stats_samtools_path = Path(subworkflow_path, "bam_stats_samtools")
    samtools_index_path = Path(self.subworkflow_install.dir, "modules", "nf-core", "modules", "samtools", "index")

    assert self.subworkflow_remove.remove("bam_sort_stats_samtools")
    assert Path.exists(subworkflow_path) is False
    assert Path.exists(bam_sort_stats_samtools_path) is False
    assert Path.exists(bam_stats_samtools_path) is False
    assert Path.exists(samtools_index_path) is False


def test_subworkflows_remove_one_of_two_subworkflow(self):
    """Test removing subworkflow and all it's dependencies after installing it"""
    self.subworkflow_install.install("bam_sort_stats_samtools")
    self.subworkflow_install.install("bam_stats_samtools")

    subworkflow_path = Path(self.subworkflow_install.dir, "modules", "nf-core", "subworkflows")
    bam_sort_stats_samtools_path = Path(subworkflow_path, "bam_sort_stats_samtools")
    bam_stats_samtools_path = Path(subworkflow_path, "bam_stats_samtools")
    samtools_index_path = Path(self.subworkflow_install.dir, "modules", "nf-core", "modules", "samtools", "index")

    assert self.subworkflow_remove.remove("bam_sort_stats_samtools")

    assert Path.exists(subworkflow_path) is False
    assert Path.exists(bam_sort_stats_samtools_path) is False
    assert Path.exists(bam_stats_samtools_path) is True
    assert Path.exists(samtools_index_path) is True
