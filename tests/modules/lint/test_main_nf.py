import pytest

import nf_core.modules.lint
import nf_core.modules.patch
from nf_core.modules.lint.main_nf import check_container_link_line, check_process_labels

from ...test_modules import TestModules
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


class TestMainNf(TestModules):
    """Test main.nf functionality"""

    def test_modules_lint_registry(self):
        """Test linting the samtools module and alternative registry"""
        assert self.mods_install.install("samtools/sort")

        # Test with alternative registry
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, registry="public.ecr.aws")
        module_lint.lint(print_results=False, module="samtools/sort")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

        # Test with default registry
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="samtools/sort")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
