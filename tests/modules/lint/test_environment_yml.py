import yaml
from nf_core.modules.lint.environment_yml import environment_yml
from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
import pytest
from yaml.scanner import ScannerError
from pathlib import Path

import nf_core.modules.lint
from ...test_modules import TestModules


@pytest.mark.parametrize(
    "input_content,expected",
    [
        # Test basic sorting
        ("dependencies:\n  - zlib\n  - python\n", ["python", "zlib"]),
        # Test dict sorting
        ("dependencies:\n  - pip:\n    - b\n    - a\n  - python\n", ["python", {"pip": ["a", "b"]}]),
        # Test existing headers
        ("---\n# yaml-language-server: $schema=...\ndependencies:\n  - b\n  - a\n", ["a", "b"]),
        # Test channel sorting
        (
            "channels:\n  - conda-forge\n  - bioconda\ndependencies:\n  - python\n",
            {"channels": ["conda-forge", "bioconda"], "dependencies": ["python"]},
        ),
        # Test channel sorting with additional channels
        (
            "channels:\n  - bioconda\n  - conda-forge\n  - defaults\n  - r\n",
            {"channels": ["conda-forge", "bioconda", "defaults", "r"]},
        ),
        # Test namespaced dependencies
        (
            "dependencies:\n  - bioconda::ngscheckmate=1.0.1\n  - bioconda::bcftools=1.21\n",
            ["bioconda::bcftools=1.21", "bioconda::ngscheckmate=1.0.1"],
        ),
        # Test mixed dependencies
        (
            "dependencies:\n  - bioconda::ngscheckmate=1.0.1\n  - python\n  - bioconda::bcftools=1.21\n",
            ["bioconda::bcftools=1.21", "bioconda::ngscheckmate=1.0.1", "python"],
        ),
        # Test full environment with channels and namespaced dependencies
        (
            """
            channels:
                - conda-forge
                - bioconda
            dependencies:
                - bioconda::ngscheckmate=1.0.1
                - bioconda::bcftools=1.21
            """,
            {
                "channels": ["conda-forge", "bioconda"],
                "dependencies": ["bioconda::bcftools=1.21", "bioconda::ngscheckmate=1.0.1"],
            },
        ),
    ],
    ids=[
        "basic_dependency_sorting",
        "dict_dependency_sorting",
        "existing_headers",
        "channel_sorting",
        "channel_sorting_with_additional_channels",
        "namespaced_dependencies",
        "mixed_dependencies",
        "full_environment",
    ],
)
def test_environment_yml_sorting(tmp_path, input_content, expected):
    test_file = tmp_path / "environment.yml"
    test_file.write_text(input_content)
    class DummyModule(NFCoreComponent):
        def __init__(self, path):
            self.environment_yml = path
            self.component_dir = path.parent
            self.component_name = "dummy"
            self.passed = []
            self.failed = []
            self.warned = []
    class DummyLint(ComponentLint):
        def __init__(self):
            self.modules_repo = type("repo", (), {"local_repo_dir": tmp_path})
            self.passed = []
            self.failed = []
    module = DummyModule(test_file)
    lint = DummyLint()
    (tmp_path / "modules").mkdir(exist_ok=True)
    (tmp_path / "modules" / "environment-schema.json").write_text("{}")
    environment_yml(lint, module)
    result = test_file.read_text()
    lines = result.splitlines(True)
    if lines[:2] == ["---\n", "# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json\n"]:
        parsed = yaml.safe_load("".join(lines[2:]))
    else:
        parsed = yaml.safe_load(result)
    if isinstance(expected, list):
        assert parsed["dependencies"] == expected
    else:
        for key, value in expected.items():
            assert key in parsed
            assert parsed[key] == value
    # Check linter passed for sorting
    assert any("environment_yml_sorted" in x for x in [p[0] for p in lint.passed])


def test_environment_yml_invalid_file(tmp_path):
    test_file = tmp_path / "bad.yml"
    test_file.write_text("invalid: yaml: here")
    class DummyModule(NFCoreComponent):
        def __init__(self, path):
            self.environment_yml = path
            self.component_dir = path.parent
            self.component_name = "dummy"
            self.passed = []
            self.failed = []
            self.warned = []
    class DummyLint(ComponentLint):
        def __init__(self):
            self.modules_repo = type("repo", (), {"local_repo_dir": tmp_path})
            self.passed = []
            self.failed = []
    module = DummyModule(test_file)
    lint = DummyLint()
    (tmp_path / "modules").mkdir(exist_ok=True)
    (tmp_path / "modules" / "environment-schema.json").write_text("{}")
    with pytest.raises(Exception):
        environment_yml(lint, module)


def test_environment_yml_empty_file(tmp_path):
    test_file = tmp_path / "empty.yml"
    test_file.write_text("")
    class DummyModule(NFCoreComponent):
        def __init__(self, path):
            self.environment_yml = path
            self.component_dir = path.parent
            self.component_name = "dummy"
            self.passed = []
            self.failed = []
            self.warned = []
    class DummyLint(ComponentLint):
        def __init__(self):
            self.modules_repo = type("repo", (), {"local_repo_dir": tmp_path})
            self.passed = []
            self.failed = []
    module = DummyModule(test_file)
    lint = DummyLint()
    (tmp_path / "modules").mkdir(exist_ok=True)
    (tmp_path / "modules" / "environment-schema.json").write_text("{}")
    with pytest.raises(Exception):
        environment_yml(lint, module)


def test_environment_yml_missing_dependencies(tmp_path):
    test_file = tmp_path / "no_deps.yml"
    test_file.write_text("channels:\n  - conda-forge\n")
    class DummyModule(NFCoreComponent):
        def __init__(self, path):
            self.environment_yml = path
            self.component_dir = path.parent
            self.component_name = "dummy"
            self.passed = []
            self.failed = []
            self.warned = []
    class DummyLint(ComponentLint):
        def __init__(self):
            self.modules_repo = type("repo", (), {"local_repo_dir": tmp_path})
            self.passed = []
            self.failed = []
    module = DummyModule(test_file)
    lint = DummyLint()
    (tmp_path / "modules").mkdir(exist_ok=True)
    (tmp_path / "modules" / "environment-schema.json").write_text("{}")
    environment_yml(lint, module)
    result = test_file.read_text()
    lines = result.splitlines(True)
    if lines[:2] == ["---\n", "# yaml-language-server: $schema=https://raw.githubusercontent.com/nf-core/modules/master/modules/environment-schema.json\n"]:
        parsed = yaml.safe_load("".join(lines[2:]))
    else:
        parsed = yaml.safe_load(result)
    assert "channels" in parsed
    assert parsed["channels"] == ["conda-forge"]
    assert "dependencies" not in parsed


# Integration tests using the full ModuleLint class

class TestModulesEnvironmentYml(TestModules):
    """Integration tests for environment.yml linting using real modules"""

    def test_modules_environment_yml_file_doesnt_exists(self):
        """Test linting a module with an environment.yml file"""
        (self.bpipe_test_module_path / "environment.yml").rename(self.bpipe_test_module_path / "environment.yml.bak")
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        (self.bpipe_test_module_path / "environment.yml.bak").rename(self.bpipe_test_module_path / "environment.yml")
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
        with open(self.bpipe_test_module_path / "environment.yml") as fh:
            yaml_content = yaml.safe_load(fh)
        # Add a new dependency to the environment.yml file and reverse the order
        yaml_content["dependencies"].append("z=0.0.0")
        yaml_content["dependencies"].reverse()
        yaml_content = yaml.dump(yaml_content)
        with open(self.bpipe_test_module_path / "environment.yml", "w") as fh:
            fh.write(yaml_content)
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        # we fix the sorting on the fly, so this should pass
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_environment_yml_file_not_array(self):
        """Test linting a module with an incorrectly formatted environment.yml file"""
        with open(self.bpipe_test_module_path / "environment.yml") as fh:
            yaml_content = yaml.safe_load(fh)
        yaml_content["dependencies"] = "z"
        with open(self.bpipe_test_module_path / "environment.yml", "w") as fh:
            fh.write(yaml.dump(yaml_content))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")
        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "environment_yml_valid"

    def test_modules_environment_yml_file_mixed_dependencies(self):
        """Test linting a module with mixed-type dependencies (strings and pip dict)"""
        with open(self.bpipe_test_module_path / "environment.yml") as fh:
            yaml_content = yaml.safe_load(fh)

        # Create mixed dependencies with strings and pip dict in wrong order
        yaml_content["dependencies"] = [
            "python=3.8",
            {"pip": ["zzz-package==1.0.0", "aaa-package==2.0.0"]},
            "bioconda::samtools=1.15.1",
            "bioconda::fastqc=0.12.1",
            "pip=23.3.1",
        ]

        with open(self.bpipe_test_module_path / "environment.yml", "w") as fh:
            fh.write(yaml.dump(yaml_content))

        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        # Check that the dependencies were sorted correctly
        with open(self.bpipe_test_module_path / "environment.yml") as fh:
            sorted_yaml = yaml.safe_load(fh)

        expected_deps = [
            "bioconda::fastqc=0.12.1",
            "bioconda::samtools=1.15.1",
            "pip=23.3.1",
            "python=3.8",
            {"pip": ["aaa-package==2.0.0", "zzz-package==1.0.0"]},
        ]

        assert sorted_yaml["dependencies"] == expected_deps
        assert len(module_lint.failed) == 0, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0

    def test_modules_environment_yml_file_default_channel_fails(self):
        """Test linting a module with a default channel set in the environment.yml file, which should fail"""
        with open(self.bpipe_test_module_path / "environment.yml") as fh:
            yaml_content = yaml.safe_load(fh)
        yaml_content["channels"] = ["bioconda", "default"]
        with open(self.bpipe_test_module_path / "environment.yml", "w") as fh:
            fh.write(yaml.dump(yaml_content))
        module_lint = nf_core.modules.lint.ModuleLint(directory=self.nfcore_modules)
        module_lint.lint(print_results=False, module="bpipe/test")

        assert len(module_lint.failed) == 1, f"Linting failed with {[x.__dict__ for x in module_lint.failed]}"
        assert len(module_lint.passed) > 0
        assert len(module_lint.warned) >= 0
        assert module_lint.failed[0].lint_test == "environment_yml_valid"
