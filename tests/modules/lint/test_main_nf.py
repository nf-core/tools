import pytest

import nf_core.modules.lint
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.modules.lint.main_nf import (
    _parse_output_topics,
    check_container_link_line,
    check_process_labels,
    check_script_section,
)

from ...test_modules import TestModules
from ...utils import GITLAB_NFTEST_BRANCH, GITLAB_URL
from .test_lint_utils import MockModuleLint


@pytest.mark.parametrize(
    "content,passed,warned,failed",
    [
        # Valid process label
        ("label 'process_high'\ncpus 12", 1, 0, 0),
        # Non-alphanumeric characters in label
        ("label 'a:label:with:colons'\ncpus 12", 0, 2, 0),
        # Conflicting labels
        ("label 'process_high'\nlabel 'process_low'\ncpus 12", 0, 1, 0),
        # Duplicate labels
        ("label 'process_high'\nlabel 'process_high'\ncpus 12", 0, 2, 0),
        # Valid and non-standard labels
        ("label 'process_high'\nlabel 'process_extra_label'\ncpus 12", 1, 1, 0),
        # Non-standard label only
        ("label 'process_extra_label'\ncpus 12", 0, 2, 0),
        # Non-standard duplicates without quotes
        ("label process_extra_label\nlabel process_extra_label\ncpus 12", 0, 3, 0),
        # No label found
        ("cpus 12", 0, 1, 0),
    ],
)
def test_process_labels(content, passed, warned, failed):
    """Test process label validation"""
    mock_lint = MockModuleLint()
    check_process_labels(mock_lint, content.splitlines())

    assert len(mock_lint.passed) == passed
    assert len(mock_lint.warned) == warned
    assert len(mock_lint.failed) == failed


@pytest.mark.parametrize(
    "content,passed,warned,failed",
    [
        # Single-line container definition should pass
        ('container "quay.io/nf-core/gatk:4.4.0.0" //Biocontainers is missing a package', 2, 0, 0),
        # Multi-line container definition should pass
        (
            '''container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
                'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0':
                'biocontainers/gatk4:4.4.0.0--py36hdfd78af_0' }"''',
            6,
            0,
            0,
        ),
        # Space in container URL should fail
        (
            '''container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
                'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0 ':
                'biocontainers/gatk4:4.4.0.0--py36hdfd78af_0' }"''',
            5,
            0,
            1,
        ),
        # Incorrect quoting of container string should fail
        (
            '''container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
                'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0 ':
                "biocontainers/gatk4:4.4.0.0--py36hdfd78af_0" }"''',
            4,
            0,
            1,
        ),
        # Ternary with ? on next line (new Nextflow format) should pass
        (
            '''container "${workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container
        ? 'https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/c2/c262fc09eca59edb5a724080eeceb00fb06396f510aefb229c2d2c6897e63975/data'
        : 'community.wave.seqera.io/library/coreutils:9.5--ae99c88a9b28c264'}"''',
            6,
            0,
            0,
        ),
    ],
)
def test_container_links(content, passed, warned, failed):
    """Test container link validation"""
    mock_lint = MockModuleLint()

    for line in content.splitlines():
        if line.strip():
            check_container_link_line(mock_lint, line, registry="quay.io")

    assert len(mock_lint.passed) == passed
    assert len(mock_lint.warned) == warned
    assert len(mock_lint.failed) == failed


class TestMainNfLinting(TestModules):
    """
    Test main.nf linting functionality.

    This class tests various aspects of main.nf file linting including:
    - Process label validation and standards compliance
    - Container definition syntax and URL validation
    - Integration testing with alternative registries
    - General module linting workflow
    """

    def setUp(self):
        """Set up test fixtures by installing required modules"""
        super().setUp()
        # Install samtools/sort module for all tests in this class
        if not self.mods_install.install("samtools/sort"):
            self.skipTest("Could not install samtools/sort module")
        if not self.mods_install.install("bamstats/generalstats"):
            self.skipTest("Could not install samtools/sort module")

    def test_main_nf_lint_with_alternative_registry(self):
        """Test main.nf linting with alternative container registry"""
        # Test with alternative registry - should warn/fail when containers don't match the registry
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, registry="public.ecr.aws")
        module_lint.lint(print_results=False, module="samtools/sort")

        # Alternative registry should produce warnings or failures for container mismatches
        # since samtools/sort module likely uses biocontainers/quay.io, not public.ecr.aws
        total_issues = len(module_lint.failed) + len(module_lint.warned)
        assert total_issues > 0, (
            "Expected warnings/failures when using alternative registry that doesn't match module containers"
        )

        # Test with default registry - should pass cleanly
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="samtools/sort")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0

    def test_topics_and_emits_version_check(self):
        """Test that main_nf version emit and topics check works correctly"""

        self.mods_install_gitlab_nftest.install("fastqc")
        # Lint a module installed from the gitlab test branch; gitlab test modules that is known to have versions YAML in main.nf
        module_lint = nf_core.modules.lint.ModuleLint(
            directory=self.pipeline_dir, remote_url=GITLAB_URL, branch=GITLAB_NFTEST_BRANCH
        )
        module_lint.lint(print_results=False, module="fastqc")
        assert any(f.lint_test in ("main_nf_version_emit", "main_nf_version_topic") for f in module_lint.failed), (
            f"Expected failure about missing version topic, got {[f.message for f in module_lint.failed]}"
        )
        assert len(module_lint.passed) > 0

        # Lint a module known to have topics as output in main.nf
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="bamstats/generalstats")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.warned) == 0, f"Expected 0 warnings, got {[x.__dict__ for x in module_lint.warned]}"

        assert len(module_lint.passed) > 0


def test_get_inputs_no_partial_keyword_match(tmp_path):
    """Test that input parsing doesn't match keywords within larger words like 'evaluate' or 'pathogen'"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)
    path(reads)
    tuple val(evaluate), path(pathogen)

    output:
    path("*.txt"), emit: results

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()

    # Should find 3 inputs: meta, reads, and the tuple (evaluate, pathogen)
    # The regex with \b should correctly identify 'val(evaluate)' and 'path(pathogen)' as valid inputs
    assert len(component.inputs) == 3, f"Expected 3 inputs, got {len(component.inputs)}: {component.inputs}"
    assert {"meta": {}} in component.inputs
    assert {"reads": {}} in component.inputs
    # The tuple should be captured as a list of two elements
    tuple_input = [{"evaluate": {}}, {"pathogen": {}}]
    assert tuple_input in component.inputs


def test_get_outputs_no_partial_keyword_match(tmp_path):
    """Test that output parsing doesn't match keywords within larger words like 'evaluate' or 'pathogen'"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    path("*.txt"), emit: results
    val(evaluate_result), emit: evaluation
    path(pathogen_data), emit: pathogens
    tuple val(meta), path("*{3prime,5prime,trimmed,val}{,_1,_2}.fq.gz"), emit: reads

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_outputs_from_main_nf()

    # Should find 4 outputs with variable names containing 'val' and 'path' substrings
    # The regex with \b should correctly identify val(evaluate_result) and path(pathogen_data)
    assert len(component.outputs) == 4, f"Expected 4 outputs, got {len(component.outputs)}: {component.outputs}"
    assert "results" in component.outputs
    assert "evaluation" in component.outputs
    assert "pathogens" in component.outputs
    assert "reads" in component.outputs
    assert '"*{3prime,5prime,trimmed,val}{,_1,_2}.fq.gz"' in list(component.outputs["reads"][0][1].keys())


def test_get_outputs_complete_version_command(tmp_path):
    """Test that the version command is complete with both eval() and val()"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    path("*.txt"), emit: results
    val(evaluate_result), emit: evaluation
    tuple val("${task.process}"), val('stranger'), eval("stranger --version | sed 's/stranger, version //g'"), topic: versions, emit: versions_stranger
    tuple val("${task.process}"), val('fastqc'), eval('fastqc --version | sed "/FastQC v/!d; s/.*v//"'), emit: versions_fastqc, topic: versions
    tuple val("${task.process}"), val('fastk'), val('1.0'), emit: versions_fastk, topic: versions


    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_outputs_from_main_nf()

    assert len(component.outputs) == 5, f"Expected 5 outputs, got {len(component.outputs)}: {component.outputs}"
    assert "results" in component.outputs
    assert "evaluation" in component.outputs
    assert "versions_stranger" in component.outputs
    assert "versions_fastqc" in component.outputs
    assert "versions_fastk" in component.outputs
    assert "\"stranger --version | sed 's/stranger, version //g'\"" in list(
        component.outputs["versions_stranger"][0][2].keys()
    )
    assert "'fastqc --version | sed \"/FastQC v/!d; s/.*v//\"'" in list(
        component.outputs["versions_fastqc"][0][2].keys()
    )
    # Check that val() for hardcoded version is also captured
    assert "'1.0'" in list(component.outputs["versions_fastk"][0][2].keys())


def test_get_topics_no_partial_keyword_match(tmp_path):
    """Test that topic parsing doesn't match keywords within larger words like 'evaluate'"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    path("*.txt"), topic: results
    val(evaluate_result), topic: evaluation

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_topics_from_main_nf()

    # Should find 2 topics with variable names containing 'val' substring
    # The regex with \b should correctly identify val(evaluate_result)
    assert len(component.topics) == 2, f"Expected 2 topics, got {len(component.topics)}: {component.topics}"
    assert "results" in component.topics
    assert "evaluation" in component.topics


def test_get_topics_multiple_versions_channels(tmp_path):
    """Test that multiple versions_* channels with the same topic name are correctly captured, including val() for hardcoded versions"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    tuple val("${task.process}"), val('samtools'), eval('samtools --version | head -1 | sed -e "s/samtools //"'), emit: versions_samtools, topic: versions
    tuple val("${task.process}"), val('bcftools'), eval('bcftools --version | head -1 | sed -e "s/bcftools //"'), emit: versions_bcftools, topic: versions
    tuple val("${task.process}"), val('fastk'), val('1.0'), emit: versions_fastk, topic: versions
    path("*.txt"), emit: results, topic: results

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_topics_from_main_nf()

    # Should find 2 topics: versions and results
    assert len(component.topics) == 2, f"Expected 2 topics, got {len(component.topics)}: {component.topics}"
    assert "versions" in component.topics
    assert "results" in component.topics

    # The versions topic should have 3 entries (two with eval(), one with val())
    assert len(component.topics["versions"]) == 3, (
        f"Expected 3 entries in versions topic, got {len(component.topics['versions'])}: {component.topics['versions']}"
    )

    # Each entry should be a list of 3 tuples elements
    for entry in component.topics["versions"]:
        assert isinstance(entry, list), f"Expected list, got {type(entry)}"
        assert len(entry) == 3, f"Expected 3 elements in entry, got {len(entry)}: {entry}"


def test_get_outputs_with_hidden_attribute(tmp_path):
    """Test that output parsing correctly handles path modifiers like 'hidden: true'"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    tuple val(meta), path("*.{prof,pidx}*", hidden: true), emit: prof, optional: true
    path("*.txt"), emit: results
    path("data.csv", hidden: true), emit: data

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_outputs_from_main_nf()

    # Should find 3 outputs
    assert len(component.outputs) == 3, f"Expected 3 outputs, got {len(component.outputs)}: {component.outputs}"
    assert "prof" in component.outputs
    assert "results" in component.outputs
    assert "data" in component.outputs

    # The prof output should only contain the pattern, not the 'hidden: true' modifier
    prof_output = component.outputs["prof"]
    assert len(prof_output) == 1, f"Expected 1 element in prof output, got {len(prof_output)}"
    assert len(prof_output[0]) == 2, f"Expected 2 elements in tuple, got {len(prof_output[0])}: {prof_output[0]}"

    # Check that the path pattern doesn't include "hidden: true"
    path_key = list(prof_output[0][1].keys())[0]
    assert '"*.{prof,pidx}*"' == path_key, f"Expected '\"*.{{prof,pidx}}*\"', got '{path_key}'"
    assert "hidden" not in path_key, f"Pattern should not contain 'hidden': {path_key}"

    # Check the data output also doesn't include "hidden: true"
    data_output = component.outputs["data"]
    data_path_key = list(data_output[0].keys())[0]
    assert '"data.csv"' == data_path_key, f"Expected '\"data.csv\"', got '{data_path_key}'"
    assert "hidden" not in data_path_key, f"Pattern should not contain 'hidden': {data_path_key}"


def test_get_outputs_with_whitespace_after_parenthesis(tmp_path):
    """Test that output parsing correctly handles spaces after parentheses like val( meta )"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    tuple val( meta ), path("*.thing"), emit: my_channel

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_outputs_from_main_nf()

    assert "my_channel" in component.outputs
    my_channel_output = component.outputs["my_channel"]
    output_keys = [list(out.keys())[0] for out in my_channel_output[0]]
    # Check that meta is correctly parsed despite the whitespace
    assert "meta" in output_keys, f"Expected 'meta' without spaces in output, got {output_keys}"


def test_get_topics_version_yml_path_no_parens(tmp_path):
    """Test that path "versions.yml" (without parentheses) with topic: versions is correctly parsed"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    val(meta)

    output:
    path "versions.yml", emit: versions, topic: versions

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_topics_from_main_nf()

    assert "versions" in component.topics, f"Expected 'versions' topic, got: {component.topics}"
    assert len(component.topics["versions"]) == 1, (
        f"Expected 1 entry in versions topic, got {len(component.topics['versions'])}: {component.topics['versions']}"
    )
    entry = component.topics["versions"][0]
    assert isinstance(entry, dict), f"Expected dict entry for single path output, got {type(entry)}"
    assert '"versions.yml"' in entry, f"Expected '\"versions.yml\"' key in entry, got: {entry}"

    # Verify linting: emit: versions on path "versions.yml" should pass wrong_version_yml_emit
    correct_line = '    path "versions.yml", emit: versions, topic: versions'
    mock_lint = MockModuleLint()
    _parse_output_topics(mock_lint, correct_line)
    assert any("wrong_version_yml_emit" in str(p) for p in mock_lint.passed), (
        f"Expected wrong_version_yml_emit in passed, got: {mock_lint.passed}"
    )
    assert mock_lint.failed == [], f"Expected no failures for correct emit, got: {mock_lint.failed}"

    # Verify linting: wrong emit name on path "versions.yml" should fail wrong_versions_yml_emit
    wrong_line = '    path "versions.yml", emit: wrong_name, topic: versions'
    mock_lint_fail = MockModuleLint()
    _parse_output_topics(mock_lint_fail, wrong_line)
    assert any("wrong_versions_yml_emit" in str(f) for f in mock_lint_fail.failed), (
        f"Expected wrong_versions_yml_emit in failed, got: {mock_lint_fail.failed}"
    )


def test_meta_input_names_valid_sequential(tmp_path):
    """Test that valid sequential meta input names (meta, meta2, meta3, meta4) pass validation"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)
    tuple val(meta2), path(index)
    tuple val(meta3), path(database)
    tuple val(meta4), path(reference)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(p) for p in mock_lint.passed), (
        f"Expected meta_input_names in passed, got: {mock_lint.passed}"
    )
    assert len(mock_lint.failed) == 0, f"Expected no failures, got: {mock_lint.failed}"
    assert len(mock_lint.warned) == 0, f"Expected no warnings, got: {mock_lint.warned}"


def test_meta_input_names_invalid_underscore(tmp_path):
    """Test that invalid meta input names with underscores (meta_vcf, meta_gex) fail validation"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta_vcf), path(reads)
    tuple val(meta_gex), path(index)
    val(meta_ab)

    output:
    tuple val(meta_vcf), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(f) for f in mock_lint.failed), (
        f"Expected meta_input_names in failed, got: {mock_lint.failed}"
    )
    # Check that the error message mentions the invalid names
    failed_msg = str(mock_lint.failed[0])
    assert "meta_vcf" in failed_msg, f"Expected 'meta_vcf' in error message, got: {failed_msg}"
    assert "meta_gex" in failed_msg, f"Expected 'meta_gex' in error message, got: {failed_msg}"
    assert "meta_ab" in failed_msg, f"Expected 'meta_ab' in error message, got: {failed_msg}"


def test_meta_input_names_invalid_meta1(tmp_path):
    """Test that meta0 and meta1 fail validation (only meta, meta2, meta3... are allowed)"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)
    tuple val(meta0), path(index)
    tuple val(meta1), path(database)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(f) for f in mock_lint.failed), (
        f"Expected meta_input_names in failed, got: {mock_lint.failed}"
    )
    failed_msg = str(mock_lint.failed[0])
    assert "meta0" in failed_msg, f"Expected 'meta0' in error message, got: {failed_msg}"
    assert "meta1" in failed_msg, f"Expected 'meta1' in error message, got: {failed_msg}"


def test_meta_input_names_invalid_leading_zeros(tmp_path):
    """Test that meta variables with leading zeros (meta01, meta02, meta003) fail validation"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)
    tuple val(meta01), path(index)
    tuple val(meta02), path(database)
    tuple val(meta003), path(reference)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(f) for f in mock_lint.failed), (
        f"Expected meta_input_names in failed, got: {mock_lint.failed}"
    )
    failed_msg = str(mock_lint.failed[0])
    assert "meta01" in failed_msg, f"Expected 'meta01' in error message, got: {failed_msg}"
    assert "meta02" in failed_msg, f"Expected 'meta02' in error message, got: {failed_msg}"
    assert "meta003" in failed_msg, f"Expected 'meta003' in error message, got: {failed_msg}"


def test_meta_input_names_non_sequential_order(tmp_path):
    """Test that non-sequential meta numbering (meta, meta3, meta2) produces a warning"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)
    tuple val(meta3), path(database)
    tuple val(meta2), path(index)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(w) for w in mock_lint.warned), (
        f"Expected meta_input_names in warned, got: {mock_lint.warned}"
    )
    warned_msg = str(mock_lint.warned[0])
    assert "sequential" in warned_msg.lower(), f"Expected 'sequential' in warning message, got: {warned_msg}"


def test_meta_input_names_gap_in_sequence(tmp_path):
    """Test that meta numbering with gaps (meta, meta2, meta5) produces a warning"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)
    tuple val(meta2), path(index)
    tuple val(meta5), path(database)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(w) for w in mock_lint.warned), (
        f"Expected meta_input_names in warned, got: {mock_lint.warned}"
    )
    warned_msg = str(mock_lint.warned[0])
    assert "sequential" in warned_msg.lower(), f"Expected 'sequential' in warning message, got: {warned_msg}"


def test_meta_input_names_no_meta_variables(tmp_path):
    """Test that modules without meta inputs don't trigger validation"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    path(reads)
    val(sample_id)
    tuple val(condition), path(reference)

    output:
    path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    # Should have no passed/failed/warned for meta_input_names since there are no meta inputs
    assert not any("meta_input_names" in str(p) for p in mock_lint.passed), (
        f"Should not have meta_input_names in passed when no meta vars, got: {mock_lint.passed}"
    )
    assert not any("meta_input_names" in str(f) for f in mock_lint.failed), (
        f"Should not have meta_input_names in failed when no meta vars, got: {mock_lint.failed}"
    )
    assert not any("meta_input_names" in str(w) for w in mock_lint.warned), (
        f"Should not have meta_input_names in warned when no meta vars, got: {mock_lint.warned}"
    )


def test_meta_input_names_only_meta(tmp_path):
    """Test that a single 'meta' input passes validation"""
    main_nf_content = """
process TEST_PROCESS {
    input:
    tuple val(meta), path(reads)

    output:
    tuple val(meta), path("*.bam"), emit: bam

    script:
    "echo test"
}
"""
    main_nf_path = tmp_path / "main.nf"
    main_nf_path.write_text(main_nf_content)

    mock_lint = MockModuleLint()
    mock_lint.main_nf = main_nf_path

    component = NFCoreComponent(
        component_name="test",
        repo_url=None,
        component_dir=tmp_path,
        repo_type="modules",
        base_dir=tmp_path,
        component_type="modules",
        remote_component=False,
    )

    component.get_inputs_from_main_nf()
    flattened_inputs = []
    for inputs in component.inputs:
        if isinstance(inputs, list):
            flattened_inputs.extend([list(i.keys())[0] for i in inputs])
        else:
            flattened_inputs.append(list(inputs.keys())[0])

    from nf_core.modules.lint.main_nf import check_meta_input_names

    check_meta_input_names(mock_lint, flattened_inputs)

    assert any("meta_input_names" in str(p) for p in mock_lint.passed), (
        f"Expected meta_input_names in passed, got: {mock_lint.passed}"
    )
    assert len(mock_lint.failed) == 0, f"Expected no failures, got: {mock_lint.failed}"
    assert len(mock_lint.warned) == 0, f"Expected no warnings, got: {mock_lint.warned}"


def test_validate_meta_keys():
    """Test validation of meta keys in script"""
    mock_lint = MockModuleLint()

    # Valid meta keys
    check_script_section(
        mock_lint,
        [
            """
    def prefix = "${meta.id}"
    def se = meta.single_end
    def id = meta.subMap(['id'])
    def m2id = meta2?.id
    """
        ],
    )
    assert len(mock_lint.failed) == 0

    # Invalid meta keys
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def sample = meta.sample
    def strand = meta.strandedness
    def m2opts = meta2?.options
    """
        ],
    )
    assert len(mock_lint.failed) == 1
    assert "meta.sample" in mock_lint.failed[0][2]
    assert "meta.strandedness" in mock_lint.failed[0][2]
    assert "meta2?.options" in mock_lint.failed[0][2]

    # meta2/meta3 with valid keys
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def id1 = meta?.id
    def id2 = meta2.id
    def se = meta3.single_end
    """
        ],
    )
    assert len(mock_lint.failed) == 0

    # Mix of valid and invalid
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def prefix = task.ext.prefix ?: "${meta.id}"
    def sample = meta.sample
    def single_end = meta.single_end
    def custom = meta2.custom_field
    """
        ],
    )
    assert len(mock_lint.failed) == 1
    assert "meta.sample" in mock_lint.failed[0][2]
    assert "meta2.custom_field" in mock_lint.failed[0][2]


def test_validate_ext_keys():
    """Test validation of ext keys in script"""
    mock_lint = MockModuleLint()

    # Valid ext keys
    check_script_section(
        mock_lint,
        [
            """
    def args = task.ext.args ?: ''
    def args2 = task.ext.args2 ?: ''
    def args3 = task.ext.args3 ?: ''
    def prefix = task.ext.prefix ?: "${meta.id}"
    def use_gpu = task.ext.use_gpu ? '--gpu' : ''
    """
        ],
    )
    assert len(mock_lint.failed) == 0

    # Invalid ext keys
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def args1 = task.ext.args1 ?: ''
    def custom = task.ext.custom ?: ''
    def suffix = task.ext.suffix ?: '.bam'
    """
        ],
    )
    assert len(mock_lint.failed) == 1
    assert "ext.args1" in mock_lint.failed[0][2]
    assert "ext.custom" in mock_lint.failed[0][2]
    assert "ext.suffix" in mock_lint.failed[0][2]

    # ext.argsN where N >= 2 should be valid
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def args2 = task.ext.args2 ?: ''
    def args10 = task.ext.args10 ?: ''
    def args99 = task.ext.args99 ?: ''
    """
        ],
    )
    assert len(mock_lint.failed) == 0

    # Check false positive matches, e.g. text.tokenize()
    mock_lint.passed, mock_lint.failed = [], []
    check_script_section(
        mock_lint,
        [
            """
    def header = file(reference).text.tokenize('\n').first()
    def input = context.trim()
    """
        ],
    )
    assert len(mock_lint.failed) == 0
