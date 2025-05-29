import ruamel.yaml
from nf_core.modules.lint.environment_yml import environment_yml
from nf_core.components.lint import ComponentLint, LintExceptionError
from nf_core.components.nfcore_component import NFCoreComponent
import pytest
from ruamel.yaml.scanner import ScannerError

yaml = ruamel.yaml.YAML()
yaml.indent(mapping=2, sequence=2, offset=2)


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
        parsed = yaml.load("".join(lines[2:]))
    else:
        parsed = yaml.load(result)
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
        parsed = yaml.load("".join(lines[2:]))
    else:
        parsed = yaml.load(result)
    assert "channels" in parsed
    assert parsed["channels"] == ["conda-forge"]
    assert "dependencies" not in parsed
