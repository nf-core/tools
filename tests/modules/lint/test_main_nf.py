PROCESS_LABEL_GOOD = (
    """
    label 'process_high'
    cpus 12
    """,
    1,
    0,
    0,
)
PROCESS_LABEL_NON_ALPHANUMERIC = (
    """
    label 'a:label:with:colons'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_GOOD_CONFLICTING = (
    """
    label 'process_high'
    label 'process_low'
    cpus 12
    """,
    0,
    1,
    0,
)
PROCESS_LABEL_GOOD_DUPLICATES = (
    """
    label 'process_high'
    label 'process_high'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_GOOD_AND_NONSTANDARD = (
    """
    label 'process_high'
    label 'process_extra_label'
    cpus 12
    """,
    1,
    1,
    0,
)
PROCESS_LABEL_NONSTANDARD = (
    """
    label 'process_extra_label'
    cpus 12
    """,
    0,
    2,
    0,
)
PROCESS_LABEL_NONSTANDARD_DUPLICATES = (
    """
    label process_extra_label
    label process_extra_label
    cpus 12
    """,
    0,
    3,
    0,
)
PROCESS_LABEL_NONE_FOUND = (
    """
    cpus 12
    """,
    0,
    1,
    0,
)

PROCESS_LABEL_TEST_CASES = [
    PROCESS_LABEL_GOOD,
    PROCESS_LABEL_NON_ALPHANUMERIC,
    PROCESS_LABEL_GOOD_CONFLICTING,
    PROCESS_LABEL_GOOD_DUPLICATES,
    PROCESS_LABEL_GOOD_AND_NONSTANDARD,
    PROCESS_LABEL_NONSTANDARD,
    PROCESS_LABEL_NONSTANDARD_DUPLICATES,
    PROCESS_LABEL_NONE_FOUND,
]


# Test cases for linting the container definitions

CONTAINER_SINGLE_GOOD = (
    "Single-line container definition should pass",
    """
    container "quay.io/nf-core/gatk:4.4.0.0" //Biocontainers is missing a package
    """,
    2,  # passed
    0,  # warned
    0,  # failed
)

CONTAINER_TWO_LINKS_GOOD = (
    "Multi-line container definition should pass",
    """
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0':
        'biocontainers/gatk4:4.4.0.0--py36hdfd78af_0' }"
    """,
    6,
    0,
    0,
)

CONTAINER_WITH_SPACE_BAD = (
    "Space in container URL should fail",
    """
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0 ':
        'biocontainers/gatk4:4.4.0.0--py36hdfd78af_0' }"
    """,
    5,
    0,
    1,
)

CONTAINER_MULTIPLE_DBLQUOTES_BAD = (
    "Incorrect quoting of container string should fail",
    """
    container "${ workflow.containerEngine == 'singularity' && !task.ext.singularity_pull_docker_container ?
        'https://depot.galaxyproject.org/singularity/gatk4:4.4.0.0--py36hdfd78af_0 ':
        "biocontainers/gatk4:4.4.0.0--py36hdfd78af_0" }"
    """,
    4,
    0,
    1,
)

CONTAINER_TEST_CASES = [
    CONTAINER_SINGLE_GOOD,
    CONTAINER_TWO_LINKS_GOOD,
    CONTAINER_WITH_SPACE_BAD,
    CONTAINER_MULTIPLE_DBLQUOTES_BAD,
]



    def test_modules_lint_registry(self):
        """Test linting the samtools module and alternative registry"""
        assert self.mods_install.install("samtools/sort")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, registry="public.ecr.aws")
        module_lint.lint(print_results=False, module="samtools/sort")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="samtools/sort")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_check_process_labels(self):
        for test_case in PROCESS_LABEL_TEST_CASES:
            process, passed, warned, failed = test_case
            mocked_ModuleLint = MockModuleLint()
            check_process_labels(mocked_ModuleLint, process.splitlines())
            assert len(mocked_ModuleLint.passed) == passed
            assert len(mocked_ModuleLint.warned) == warned
            assert len(mocked_ModuleLint.failed) == failed

    def test_modules_lint_check_url(self):
        for test_case in CONTAINER_TEST_CASES:
            test, process, passed, warned, failed = test_case
            mocked_ModuleLint = MockModuleLint()
            for line in process.splitlines():
                if line.strip():
                    check_container_link_line(mocked_ModuleLint, line, registry="quay.io")

            assert len(mocked_ModuleLint.passed) == passed, (
                f"{test}: Expected {passed} PASS, got {len(mocked_ModuleLint.passed)}."
            )
            assert len(mocked_ModuleLint.warned) == warned, (
                f"{test}: Expected {warned} WARN, got {len(mocked_ModuleLint.warned)}."
            )
            assert len(mocked_ModuleLint.failed) == failed, (
                f"{test}: Expected {failed} FAIL, got {len(mocked_ModuleLint.failed)}."
            )