from pathlib import Path

import pytest

from nf_core.components.nfcore_component import NFCoreComponent


@pytest.mark.parametrize(
    "include_line,expected",
    [
        # Module from the same org
        (
            "include { SAMTOOLS_SORT } from '../../../modules/nf-core/samtools/sort/main'",
            ["samtools/sort"],
        ),
        # Sibling subworkflow
        (
            "include { BAM_SORT_STATS_SAMTOOLS } from '../bam_sort_stats_samtools/main'",
            ["subworkflows/bam_sort_stats_samtools"],
        ),
        # Aliased sibling subworkflow
        (
            "include { BAM_SORT_STATS_SAMTOOLS as BAM_SORT } from '../bam_sort_stats_samtools/main'",
            ["subworkflows/bam_sort_stats_samtools"],
        ),
        # Sibling subworkflow with double quotes
        (
            'include { BAM_SORT_STATS_SAMTOOLS } from "../bam_sort_stats_samtools/main"',
            ["subworkflows/bam_sort_stats_samtools"],
        ),
        # Sibling subworkflow included by its directory
        (
            "include { FASTQ_QC_STATS } from '../fastq_qc_stats'",
            ["subworkflows/fastq_qc_stats"],
        ),
        # Module from another org
        (
            "include { SAMTOOLS_SORT } from '../../../modules/another_org/samtools/sort/main'",
            ["another_org/samtools/sort"],
        ),
        # Sibling subworkflow from another org
        (
            "include { BAM_SORT_STATS_SAMTOOLS } from '../../another_org/bam_sort_stats_samtools/main'",
            ["another_org/subworkflows/bam_sort_stats_samtools"],
        ),
    ],
)
def test_get_included_components_subworkflow(tmp_path: Path, include_line: str, expected: list[str]):
    """Included components are turned into the tags required in main.nf.test"""
    component_dir = tmp_path / "subworkflows" / "nf-core" / "fastq_align_star"
    component_dir.mkdir(parents=True)
    main_nf = component_dir / "main.nf"
    main_nf.write_text(f"{include_line}\n\nworkflow FASTQ_ALIGN_STAR {{\n}}\n")

    component = NFCoreComponent(
        component_name="fastq_align_star",
        repo_url=None,
        component_dir=component_dir,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="subworkflows",
        remote_component=True,
    )

    assert component.org == "nf-core"
    assert component._get_included_components(main_nf) == expected
