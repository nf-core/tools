from pathlib import Path

import pytest
import yaml

import nf_core.modules
from nf_core.modules.lint import main_nf
from nf_core.utils import set_wd

from ..utils import GITLAB_URL
from .patch import BISMARK_ALIGN, CORRECT_SHA, PATCH_BRANCH, REPO_NAME, modify_main_nf


def setup_patch(pipeline_dir: str, modify_module: bool):
    install_obj = nf_core.modules.ModuleInstall(
        pipeline_dir, prompt=False, force=False, remote_url=GITLAB_URL, branch=PATCH_BRANCH, sha=CORRECT_SHA
    )

    # Install the module
    install_obj.install(BISMARK_ALIGN)

    if modify_module:
        # Modify the module
        module_path = Path(pipeline_dir, "modules", REPO_NAME, BISMARK_ALIGN)
        modify_main_nf(module_path / "main.nf")


def test_modules_lint_trimgalore(self):
    """Test linting the TrimGalore! module"""
    self.mods_install.install("trimgalore")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, module="trimgalore")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_empty(self):
    """Test linting a pipeline with no modules installed"""
    self.mods_remove.remove("fastqc", force=True)
    self.mods_remove.remove("multiqc", force=True)
    self.mods_remove.remove("custom/dumpsoftwareversions", force=True)
    with pytest.raises(LookupError):
        nf_core.modules.ModuleLint(dir=self.pipeline_dir)


def test_modules_lint_new_modules(self):
    """lint a new module"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_no_gitlab(self):
    """Test linting a pipeline with no modules installed"""
    self.mods_remove.remove("fastqc", force=True)
    self.mods_remove.remove("multiqc", force=True)
    self.mods_remove.remove("custom/dumpsoftwareversions", force=True)
    with pytest.raises(LookupError):
        nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)


def test_modules_lint_gitlab_modules(self):
    """Lint modules from a different remote"""
    self.mods_install_gitlab.install("fastqc")
    self.mods_install_gitlab.install("multiqc")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 2
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_multiple_remotes(self):
    """Lint modules from a different remote"""
    self.mods_install_gitlab.install("multiqc")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, remote_url=GITLAB_URL)
    module_lint.lint(print_results=False, all_modules=True)
    assert len(module_lint.failed) == 1
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_registry(self):
    """Test linting the samtools module and alternative registry"""
    self.mods_install.install("samtools")
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir, registry="public.ecr.aws")
    module_lint.lint(print_results=False, module="samtools")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    module_lint = nf_core.modules.ModuleLint(dir=self.pipeline_dir)
    module_lint.lint(print_results=False, module="samtools")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_patched_modules(self):
    """
    Test creating a patch file and applying it to a new version of the the files
    """
    setup_patch(self.pipeline_dir, True)

    # Create a patch file
    patch_obj = nf_core.modules.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
    patch_obj.patch(BISMARK_ALIGN)

    # change temporarily working directory to the pipeline directory
    # to avoid error from try_apply_patch() during linting
    with set_wd(self.pipeline_dir):
        module_lint = nf_core.modules.ModuleLint(
            dir=self.pipeline_dir, remote_url=GITLAB_URL, branch=PATCH_BRANCH, hide_progress=True
        )
        module_lint.lint(
            print_results=False,
            all_modules=True,
        )

    assert len(module_lint.failed) == 1
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


# A skeleton object with the passed/warned/failed list attrs
# Use this in place of a ModuleLint object to test behaviour of
# linting methods which don't need the full setup
class MockModuleLint:
    def __init__(self):
        self.passed = []
        self.warned = []
        self.failed = []

        self.main_nf = "main_nf"


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


def test_modules_lint_check_process_labels(self):
    for test_case in PROCESS_LABEL_TEST_CASES:
        process, passed, warned, failed = test_case
        mocked_ModuleLint = MockModuleLint()
        main_nf.check_process_labels(mocked_ModuleLint, process.splitlines())
        assert len(mocked_ModuleLint.passed) == passed
        assert len(mocked_ModuleLint.warned) == warned
        assert len(mocked_ModuleLint.failed) == failed


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


def test_modules_lint_check_url(self):
    for test_case in CONTAINER_TEST_CASES:
        test, process, passed, warned, failed = test_case
        mocked_ModuleLint = MockModuleLint()
        for line in process.splitlines():
            if line.strip():
                main_nf.check_container_link_line(mocked_ModuleLint, line, registry="quay.io")

        assert (
            len(mocked_ModuleLint.passed) == passed
        ), f"{test}: Expected {passed} PASS, got {len(mocked_ModuleLint.passed)}."
        assert (
            len(mocked_ModuleLint.warned) == warned
        ), f"{test}: Expected {warned} WARN, got {len(mocked_ModuleLint.warned)}."
        assert (
            len(mocked_ModuleLint.failed) == failed
        ), f"{test}: Expected {failed} FAIL, got {len(mocked_ModuleLint.failed)}."


def test_modules_lint_snapshot_file(self):
    """Test linting a module with a snapshot file"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_lint_snapshot_file_missing_fail(self):
    """Test linting a module with a snapshot file missing, which should fail"""
    Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test.snap").unlink()
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test.snap").touch()
    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    assert module_lint.failed[0].lint_test == "test_snapshot_exists"


def test_modules_lint_snapshot_file_not_needed(self):
    """Test linting a module which doesn't need a snapshot file by removing the snapshot keyword in the main.nf.test file"""
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test"), "r") as fh:
        content = fh.read()
        new_content = content.replace("snapshot(", "snap (")
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests", "main.nf.test"), "w") as fh:
        fh.write(new_content)
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_environment_yml_file_doesnt_exists(self):
    """Test linting a module with an environment.yml file"""
    Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml").rename(
        Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml.bak")
    )
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml.bak").rename(
        Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")
    )
    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    assert module_lint.failed[0].lint_test == "environment_yml_exists"


def test_modules_environment_yml_file_sorted_correctly(self):
    """Test linting a module with a correctly sorted environment.yml file"""
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_environment_yml_file_sorted_incorrectly(self):
    """Test linting a module with an incorrectly sorted environment.yml file"""
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml"), "r") as fh:
        yaml_content = yaml.safe_load(fh)
    # Add a new dependency to the environment.yml file and reverse the order
    yaml_content["dependencies"].append("z")
    yaml_content["dependencies"].reverse()
    yaml_content = yaml.dump(yaml_content)
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml"), "w") as fh:
        fh.write(yaml_content)
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    # we fix the sorting on the fly, so this should pass
    assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0


def test_modules_environment_yml_file_not_array(self):
    """Test linting a module with an incorrectly formatted environment.yml file"""
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")) as fh:
        yaml_content = yaml.safe_load(fh)
    yaml_content["dependencies"] = "z"
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml"), "w") as fh:
        fh.write(yaml.dump(yaml_content))
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    assert module_lint.failed[0].lint_test == "environment_yml_valid"


def test_modules_environment_yml_file_name_mismatch(self):
    """Test linting a module with a different name in the environment.yml file"""
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")) as fh:
        yaml_content = yaml.safe_load(fh)
    yaml_content["name"] = "bpipe-test"
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml"), "w") as fh:
        fh.write(yaml.dump(yaml_content))
    module_lint = nf_core.modules.ModuleLint(dir=self.nfcore_modules)
    module_lint.lint(print_results=False, module="bpipe/test")
    # reset changes
    yaml_content["name"] = "bpipe_test"
    with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml"), "w") as fh:
        fh.write(yaml.dump(yaml_content))

    assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
    assert len(module_lint.passed) > 0
    assert len(module_lint.warned) >= 0
    assert module_lint.failed[0].lint_test == "environment_yml_name"
