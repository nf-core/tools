from pathlib import Path

import pytest

from nf_core.components.nfcore_component import NFCoreComponent


@pytest.mark.parametrize(
    "include_line,expected",
    [
        # Module from the same org without subtool
        (
            "include { PROKKA } from '../../../modules/nf-core/prokka/main'",
            ["prokka"],
        ),
        # Module from the same org with subtool
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
        # Module from another org without subtool
        (
            "include { PROKKA } from '../../../modules/another_org/prokka/main'",
            ["another_org/prokka"],
        ),
        # Module from another org with subtool
        (
            "include { SAMTOOLS_SORT } from '../../../modules/another_org/samtools/sort/main'",
            ["another_org/samtools/sort"],
        ),
        # Sibling subworkflow from another org
        (
            "include { BAM_SORT_STATS_SAMTOOLS } from '../../another_org/bam_sort_stats_samtools/main'",
            ["another_org/subworkflows/bam_sort_stats_samtools"],
        ),
        # Plugin
        (
            "include { paramsSummaryLog   } from 'plugin/nf-schema'",
            ["plugin/nf-schema"],
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


@pytest.mark.parametrize(
    "component_type,component_name,script_line,expected",
    [
        # The component's own script
        ("modules", "samtools/sort", 'script "../main.nf"', []),
        # Sibling subtool of the same tool
        ("modules", "samtools/sort", 'script "../../index/main.nf"', ["samtools/index"]),
        # Module from the same org with subtool
        ("modules", "samtools/sort", 'script "../../../bwa/mem/main.nf"', ["bwa/mem"]),
        # Module from the same org without subtool
        ("modules", "samtools/sort", 'script "../../../gunzip/main.nf"', ["gunzip"]),
        ("modules", "gunzip", 'script "../../fastqc/main.nf"', ["fastqc"]),
        ("modules", "gunzip", 'script "../../bwa/index/main.nf"', ["bwa/index"]),
        # Paths relative to the repo root
        ("modules", "samtools/sort", 'script "modules/nf-core/bwa/index/main.nf"', ["bwa/index"]),
        (
            "modules",
            "samtools/sort",
            'script "subworkflows/nf-core/bam_stats_samtools/main.nf"',
            ["subworkflows/bam_stats_samtools"],
        ),
        # Subworkflow via ../
        (
            "modules",
            "samtools/sort",
            'script "../../../../../subworkflows/nf-core/bam_stats_samtools/main.nf"',
            ["subworkflows/bam_stats_samtools"],
        ),
        # Module included from a subworkflow test
        ("subworkflows", "fastq_align_star", 'script "../../../../modules/nf-core/star/align/main.nf"', ["star/align"]),
        # Sibling subworkflow included from a subworkflow test
        (
            "subworkflows",
            "fastq_align_star",
            'script "../../bam_sort_stats_samtools/main.nf"',
            ["subworkflows/bam_sort_stats_samtools"],
        ),
        # Module from another org
        ("modules", "samtools/sort", 'script "../../../../another_org/bwa/mem/main.nf"', ["another_org/bwa/mem"]),
        ("modules", "samtools/sort", 'script "modules/another_org/bwa/mem/main.nf"', ["another_org/bwa/mem"]),
        # Subworkflow from another org
        (
            "modules",
            "samtools/sort",
            'script "subworkflows/another_org/bam_stats_samtools/main.nf"',
            ["another_org/subworkflows/bam_stats_samtools"],
        ),
    ],
)
def test_get_included_components_in_chained_tests(
    tmp_path: Path, component_type: str, component_name: str, script_line: str, expected: list[str]
):
    """Components set up in main.nf.test are turned into the tags required in main.nf.test"""
    component_dir = tmp_path / component_type / "nf-core" / component_name
    nftest_dir = component_dir / "tests"
    nftest_dir.mkdir(parents=True)
    main_nf_test = nftest_dir / "main.nf.test"
    main_nf_test.write_text(f'setup {{\n    run("COMPONENT") {{\n        {script_line}\n    }}\n}}\n')

    component = NFCoreComponent(
        component_name=component_name,
        repo_url=None,
        component_dir=component_dir,
        repo_type="modules",
        base_dir=tmp_path,
        component_type=component_type,
        remote_component=True,
    )

    assert component.org == "nf-core"
    assert component._get_included_components_in_chained_tests(main_nf_test) == expected


def test_included_components_in_subworkflow_from_another_org(tmp_path: Path):
    """Components of the subworkflow's own org get no prefix, nf-core ones get the 'nf-core/' prefix"""
    component_dir = tmp_path / "subworkflows" / "sanger-tol" / "bam_merge"
    nftest_dir = component_dir / "tests"
    nftest_dir.mkdir(parents=True)
    main_nf = component_dir / "main.nf"
    main_nf.write_text(
        "include { SAMTOOLS_FAIDX    } from '../../../modules/nf-core/samtools/faidx/main'\n"
        "include { SAMTOOLS_MERGEDUP } from '../../../modules/sanger-tol/samtools/mergedup/main'\n"
        "include { BAM_SORT_STATS_SAMTOOLS } from '../../nf-core/bam_sort_stats_samtools/main'\n"
    )
    main_nf_test = nftest_dir / "main.nf.test"
    main_nf_test.write_text(
        'script "../main.nf"\n'
        'script "../../../../modules/nf-core/samtools/faidx/main.nf"\n'
        'script "../../../../modules/sanger-tol/samtools/mergedup/main.nf"\n'
    )

    component = NFCoreComponent(
        component_name="bam_merge",
        repo_url=None,
        component_dir=component_dir,
        repo_type="pipeline",
        base_dir=tmp_path,
        component_type="subworkflows",
        remote_component=True,
    )

    assert component.org == "sanger-tol"
    assert component._get_included_components(main_nf) == [
        "nf-core/samtools/faidx",
        "samtools/mergedup",
        "nf-core/subworkflows/bam_sort_stats_samtools",
    ]
    assert component._get_included_components_in_chained_tests(main_nf_test) == [
        "nf-core/samtools/faidx",
        "samtools/mergedup",
    ]
