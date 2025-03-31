import json
import shutil
from pathlib import Path
from typing import Union

import yaml
from git.repo import Repo

import nf_core.modules.lint
import nf_core.modules.patch
from nf_core.modules.lint.main_nf import check_container_link_line, check_process_labels
from nf_core.utils import set_wd

from ..test_modules import TestModules
from ..utils import GITLAB_NFTEST_BRANCH, GITLAB_URL
from .test_patch import BISMARK_ALIGN, CORRECT_SHA, PATCH_BRANCH, REPO_NAME, modify_main_nf

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


class TestModulesLint(TestModules):
    def _setup_patch(self, pipeline_dir: Union[str, Path], modify_module: bool):
        install_obj = nf_core.modules.install.ModuleInstall(
            pipeline_dir,
            prompt=False,
            force=False,
            remote_url=GITLAB_URL,
            branch=PATCH_BRANCH,
            sha=CORRECT_SHA,
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
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="trimgalore")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_tabix_tabix(self):
        """Test linting the tabix/tabix module"""
        self.mods_install.install("tabix/tabix")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, module="tabix/tabix")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_empty(self):
        """Test linting a pipeline with no modules installed"""
        self.mods_remove.remove("fastqc", force=True)
        self.mods_remove.remove("multiqc", force=True)
        nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        assert "No modules from https://github.com/nf-core/modules.git installed in pipeline" in self.caplog.text

    def test_modules_lint_new_modules(self):
        """lint a new module"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_no_gitlab(self):
        """Test linting a pipeline with no modules installed"""
        self.mods_remove.remove("fastqc", force=True)
        self.mods_remove.remove("multiqc", force=True)
        nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        assert f"No modules from {GITLAB_URL} installed in pipeline" in self.caplog.text

    def test_modules_lint_gitlab_modules(self):
        """Lint modules from a different remote"""
        self.mods_install_gitlab.install("fastqc")
        self.mods_install_gitlab.install("multiqc")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 2
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_multiple_remotes(self):
        """Lint modules from a different remote"""
        self.mods_install_gitlab.install("multiqc")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir, remote_url=GITLAB_URL)
        module_lint.lint(print_results=False, all_modules=True)
        assert len(module_lint.failed) == 1
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

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

    def test_modules_lint_patched_modules(self):
        """
        Test creating a patch file and applying it to a new version of the the files
        """
        self._setup_patch(str(self.pipeline_dir), True)

        # Create a patch file
        patch_obj = nf_core.modules.patch.ModulePatch(self.pipeline_dir, GITLAB_URL, PATCH_BRANCH)
        patch_obj.patch(BISMARK_ALIGN)

        # change temporarily working directory to the pipeline directory
        # to avoid error from try_apply_patch() during linting
        with set_wd(self.pipeline_dir):
            module_lint = nf_core.modules.lint.ModuleLint(
                directory=self.pipeline_dir,
                remote_url=GITLAB_URL,
                branch=PATCH_BRANCH,
                hide_progress=True,
            )
            module_lint.lint(
                print_results=False,
                all_modules=True,
            )

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
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

    def test_modules_lint_update_meta_yml(self):
        """update the meta.yml of a module"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules, fix=True)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_snapshot_file(self):
        """Test linting a module with a snapshot file"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_snapshot_file_missing_fail(self):
        """Test linting a module with a snapshot file missing, which should fail"""
        Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test.snap",
        ).unlink()
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test.snap",
        ).touch()
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_snapshot_exists"

    def test_modules_lint_snapshot_file_not_needed(self):
        """Test linting a module which doesn't need a snapshot file by removing the snapshot keyword in the main.nf.test file"""
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test",
            )
        ) as fh:
            content = fh.read()
            new_content = content.replace("snapshot(", "snap (")
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test",
            ),
            "w",
        ) as fh:
            fh.write(new_content)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_environment_yml_file_doesnt_exists(self):
        """Test linting a module with an environment.yml file"""
        Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml").rename(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml.bak",
            )
        )
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "environment.yml.bak",
        ).rename(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml",
            )
        )
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "environment_yml_exists"

    def test_modules_environment_yml_file_sorted_correctly(self):
        """Test linting a module with a correctly sorted environment.yml file"""
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_environment_yml_file_sorted_incorrectly(self):
        """Test linting a module with an incorrectly sorted environment.yml file"""
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml",
            )
        ) as fh:
            yaml_content = yaml.safe_load(fh)
        # Add a new dependency to the environment.yml file and reverse the order
        yaml_content["dependencies"].append("z=0.0.0")
        yaml_content["dependencies"].reverse()
        yaml_content = yaml.dump(yaml_content)
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml",
            ),
            "w",
        ) as fh:
            fh.write(yaml_content)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        # we fix the sorting on the fly, so this should pass
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_environment_yml_file_not_array(self):
        """Test linting a module with an incorrectly formatted environment.yml file"""
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml",
            )
        ) as fh:
            yaml_content = yaml.safe_load(fh)
        yaml_content["dependencies"] = "z"
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "environment.yml",
            ),
            "w",
        ) as fh:
            fh.write(yaml.dump(yaml_content))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "environment_yml_valid"

    def test_modules_meta_yml_incorrect_licence_field(self):
        """Test linting a module with an incorrect Licence field in meta.yml"""
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)
        meta_yml["tools"][0]["bpipe"]["licence"] = "[MIT]"
        with open(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml"),
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        # reset changes
        meta_yml["tools"][0]["bpipe"]["licence"] = ["MIT"]
        with open(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml"),
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "meta_yml_valid"

    def test_modules_meta_yml_output_mismatch(self):
        """Test linting a module with an extra entry in output fields in meta.yml compared to module.output"""
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf")) as fh:
            main_nf = fh.read()
        main_nf_new = main_nf.replace("emit: sequence_report", "emit: bai")
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf"), "w") as fh:
            fh.write(main_nf_new)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "main.nf"), "w") as fh:
            fh.write(main_nf)
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert "Module `meta.yml` does not match `main.nf`" in module_lint.failed[0].message

    def test_modules_meta_yml_incorrect_name(self):
        """Test linting a module with an incorrect name in meta.yml"""
        with open(Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml")) as fh:
            meta_yml = yaml.safe_load(fh)
        meta_yml["name"] = "bpipe/test"
        with open(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml"),
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        # reset changes
        meta_yml["name"] = "bpipe_test"
        with open(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "meta.yml"),
            "w",
        ) as fh:
            fh.write(yaml.dump(meta_yml))

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "meta_name"

    def test_modules_missing_test_dir(self):
        """Test linting a module with a missing test directory"""
        Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests").rename(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests.bak")
        )
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests.bak").rename(
            Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "tests")
        )
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_dir_exists"

    def test_modules_missing_test_main_nf(self):
        """Test linting a module with a missing test/main.nf file"""
        Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test",
        ).rename(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test.bak",
            )
        )
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test.bak",
        ).rename(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test",
            )
        )
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_main_nf_exists"

    def test_modules_unused_pytest_files(self):
        """Test linting a nf-test module with files still present in `tests/modules/`"""
        Path(self.nfcore_modules, "tests", "modules", "bpipe", "test").mkdir(parents=True, exist_ok=True)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        Path(self.nfcore_modules, "tests", "modules", "bpipe", "test").rmdir()
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_old_test_dir"

    def test_nftest_failing_linting(self):
        """Test linting a module which includes other modules in nf-test tests.
        Linting tests"""
        # Clone modules repo with testing modules
        tmp_dir = self.nfcore_modules.parent
        self.nfcore_modules = Path(tmp_dir, "modules-test")
        Repo.clone_from(GITLAB_URL, self.nfcore_modules, branch=GITLAB_NFTEST_BRANCH)

        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="kallisto/quant")

        assert len(module_lint.failed) == 3, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "environment_yml_valid"
        assert module_lint.failed[1].lint_test == "meta_yml_valid"
        assert module_lint.failed[2].lint_test == "test_main_tags"
        assert "kallisto/index" in module_lint.failed[2].message

    def test_modules_absent_version(self):
        """Test linting a nf-test module if the versions is absent in the snapshot file `"""
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test.snap",
            )
        ) as fh:
            content = fh.read()
            new_content = content.replace("versions", "foo")
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test.snap",
            ),
            "w",
        ) as fh:
            fh.write(new_content)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        with open(
            Path(
                self.nfcore_modules,
                "modules",
                "nf-core",
                "bpipe",
                "test",
                "tests",
                "main.nf.test.snap",
            ),
            "w",
        ) as fh:
            fh.write(content)
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) >= 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_snap_versions"

    def test_modules_empty_file_in_snapshot(self):
        """Test linting a nf-test module with an empty file sha sum in the test snapshot, which should make it fail (if it is not a stub)"""
        snap_file = Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test.snap",
        )
        snap = json.load(snap_file.open())
        content = snap_file.read_text()
        snap["my test"]["content"][0]["0"] = "test:md5,d41d8cd98f00b204e9800998ecf8427e"

        with open(snap_file, "w") as fh:
            json.dump(snap, fh)

        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "test_snap_md5sum"

        # reset the file
        with open(snap_file, "w") as fh:
            fh.write(content)

    def test_modules_empty_file_in_stub_snapshot(self):
        """Test linting a nf-test module with an empty file sha sum in the stub test snapshot, which should make it not fail"""
        snap_file = Path(
            self.nfcore_modules,
            "modules",
            "nf-core",
            "bpipe",
            "test",
            "tests",
            "main.nf.test.snap",
        )
        snap = json.load(snap_file.open())
        content = snap_file.read_text()
        snap["my_test_stub"] = {"content": [{"0": "test:md5,d41d8cd98f00b204e9800998ecf8427e", "versions": {}}]}

        with open(snap_file, "w") as fh:
            json.dump(snap, fh)

        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert any(x.lint_test == "test_snap_md5sum" for x in module_lint.passed)

        # reset the file
        with open(snap_file, "w") as fh:
            fh.write(content)

    def test_modules_lint_local(self):
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore")
        shutil.move(installed, local)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_lint_local_missing_files(self):
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore")
        shutil.move(installed, local)
        Path(self.pipeline_dir, "modules", "local", "trimgalore", "environment.yml").unlink()
        Path(self.pipeline_dir, "modules", "local", "trimgalore", "meta.yml").unlink()
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        warnings = [x.message for x in module_lint.warned]
        assert "Module's `environment.yml` does not exist" in warnings
        assert "Module `meta.yml` does not exist" in warnings

    def test_modules_lint_local_old_format(self):
        Path(self.pipeline_dir, "modules", "local").mkdir()
        assert self.mods_install.install("trimgalore")
        installed = Path(self.pipeline_dir, "modules", "nf-core", "trimgalore", "main.nf")
        local = Path(self.pipeline_dir, "modules", "local", "trimgalore.nf")
        shutil.move(installed, local)
        self.mods_remove.remove("trimgalore", force=True)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.pipeline_dir)
        module_lint.lint(print_results=False, local=True)
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
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
