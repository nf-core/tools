from unittest import mock
from unittest.mock import patch

import nf_core.modules.modules_utils
from nf_core.modules.modules_utils import (
    get_container_with_regex,
    module_uses_dockerfile,
    scan_modules_dir,
)

from ..test_modules import TestModules


class TestModulesUtils(TestModules):
    def test_get_installed_modules(self):
        """Test getting installed modules"""
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)
        assert len(nfcore_modules) == 1
        assert nfcore_modules[0].component_name == "bpipe/test"

    def test_get_installed_modules_with_files(self):
        """Test getting installed modules. When a module contains a file in its directory, it shouldn't be picked up as a tool/subtool"""
        # Create a file in the module directory
        with open(self.nfcore_modules / "modules" / "nf-core" / "bpipe" / "test_file.txt", "w") as fh:
            fh.write("test")

        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)
        assert len(nfcore_modules) == 1

    def test_filter_modules_by_name_exact_match(self):
        """Test filtering modules by name with an exact match"""
        # install bpipe/test
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)

        # Test exact match
        filtered = nf_core.modules.modules_utils.filter_modules_by_name(nfcore_modules, "bpipe/test")
        assert len(filtered) == 1
        assert filtered[0].component_name == "bpipe/test"

    def test_filter_modules_by_name_tool_family(self):
        """Test filtering modules by name to get all subtools of a super-tool"""
        # Create some mock samtools subtools in the modules directory
        samtools_dir = self.nfcore_modules / "modules" / "nf-core" / "samtools"

        for subtool in ["view", "sort", "index"]:
            subtool_dir = samtools_dir / subtool
            subtool_dir.mkdir(parents=True, exist_ok=True)
            (subtool_dir / "main.nf").touch()

        # Get the modules
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)

        # Test filtering by tool family (super-tool)
        filtered = nf_core.modules.modules_utils.filter_modules_by_name(nfcore_modules, "samtools")

        assert {m.component_name for m in filtered} == {"samtools/view", "samtools/sort", "samtools/index"}

    def test_filter_modules_by_name_exact_match_preferred(self):
        """Test that exact matches are preferred over prefix matches"""
        # Create a samtools super-tool and its subtools
        samtools_dir = self.nfcore_modules / "modules" / "nf-core" / "samtools"
        samtools_dir.mkdir(parents=True, exist_ok=True)
        (samtools_dir / "main.nf").touch()

        # Create subtools
        for subtool in ["view", "sort"]:
            subtool_dir = samtools_dir / subtool
            subtool_dir.mkdir(parents=True, exist_ok=True)
            (subtool_dir / "main.nf").touch()

        # Get the modules
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)

        # Test that exact match is returned when it exists
        filtered = nf_core.modules.modules_utils.filter_modules_by_name(nfcore_modules, "samtools")
        assert len(filtered) == 1
        assert filtered[0].component_name == "samtools"

    def test_filter_modules_by_name_no_match(self):
        """Test filtering modules by name with no matches"""
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.nfcore_modules)

        # Test no match
        filtered = nf_core.modules.modules_utils.filter_modules_by_name(nfcore_modules, "nonexistent")
        assert len(filtered) == 0

    def test_filter_modules_by_name_empty_list(self):
        """Test filtering an empty list of modules"""
        modules = []

        filtered = nf_core.modules.modules_utils.filter_modules_by_name(modules, "fastqc")
        assert len(filtered) == 0

    def test_load_edam(self):
        """Test EDAM ontology loading"""

        with patch(
            "nf_core.modules.modules_utils.NFCORE_CACHE_DIR",
            str(self.tmp_path),
        ):
            cache_path = self.tmp_path / "EDAM.tsv"

            assert not cache_path.exists()

            edam_formats = nf_core.modules.modules_utils.load_edam()

            assert cache_path.exists()

            first_key, first_value = next(iter(edam_formats.items()))

            assert isinstance(first_key, str)
            assert isinstance(first_value, tuple)
            assert len(first_value) == 2

    def test_scan_modules_dir_returns_module_names(self):
        """Test that scan_modules_dir returns module names relative to the scanned directory"""
        modules_dir = self.nfcore_modules / "modules" / "nf-core"
        result = scan_modules_dir(modules_dir)
        assert "bpipe/test" in result

    def test_scan_modules_dir_nonexistent(self):
        """Test that scan_modules_dir returns an empty list for a nonexistent directory"""
        result = scan_modules_dir(self.nfcore_modules / "does" / "not" / "exist")
        assert result == []

    def test_scan_modules_dir_multiple_modules(self):
        """Test that scan_modules_dir returns all modules when multiple are present"""
        modules_dir = self.nfcore_modules / "modules" / "nf-core"
        extra = modules_dir / "samtools" / "sort"
        extra.mkdir(parents=True)
        (extra / "main.nf").touch()
        try:
            result = scan_modules_dir(modules_dir)
            assert "bpipe/test" in result
            assert "samtools/sort" in result
        finally:
            import shutil

            shutil.rmtree(modules_dir / "samtools")


def test_get_container_with_regex_single_line(tmp_path):
    main_nf = tmp_path / "main.nf"
    main_nf.write_text('container "quay.io/biocontainers/fastqc:0.11.9--0"\n')
    assert get_container_with_regex(main_nf) == "quay.io/biocontainers/fastqc:0.11.9--0"


def test_get_container_with_regex_single_quotes(tmp_path):
    main_nf = tmp_path / "main.nf"
    main_nf.write_text("container 'quay.io/biocontainers/fastqc:0.11.9--0'\n")
    assert get_container_with_regex(main_nf) == "quay.io/biocontainers/fastqc:0.11.9--0"


def test_get_container_with_regex_multiline(tmp_path):
    main_nf = tmp_path / "main.nf"
    main_nf.write_text(
        "container \"${ workflow.containerEngine == 'singularity' ?\n"
        "    'docker://quay.io/biocontainers/fastqc:0.11.9--0' :\n"
        "    'quay.io/biocontainers/fastqc:0.11.9--0' }\"\n"
    )
    result = get_container_with_regex(main_nf)
    assert "quay.io/biocontainers/fastqc" in result


def test_get_container_with_regex_no_container(tmp_path):
    main_nf = tmp_path / "main.nf"
    main_nf.write_text('process TEST {\n    script:\n    "echo test"\n}\n')
    assert get_container_with_regex(main_nf) == ""


def test_get_container_with_regex_container_keyword_no_match(tmp_path):
    """container keyword present but no valid quoted string returns empty."""
    main_nf = tmp_path / "main.nf"
    main_nf.write_text("// container removed\n")
    assert get_container_with_regex(main_nf) == ""


def test_module_uses_dockerfile_true(tmp_path):
    comp = mock.Mock()
    comp.component_dir = tmp_path
    comp.environment_yml = None
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
    assert module_uses_dockerfile(comp)


def test_module_uses_dockerfile_false_has_env_yml(tmp_path):
    env_yml = tmp_path / "environment.yml"
    env_yml.write_text("name: test\n")
    comp = mock.Mock()
    comp.component_dir = tmp_path
    comp.environment_yml = env_yml
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
    assert not module_uses_dockerfile(comp)


def test_module_uses_dockerfile_false_no_dockerfile(tmp_path):
    comp = mock.Mock()
    comp.component_dir = tmp_path
    comp.environment_yml = None
    assert not module_uses_dockerfile(comp)


def test_module_uses_dockerfile_nonexistent_env_yml_path(tmp_path):
    """environment_yml pointing to a non-existent file is treated as missing."""
    comp = mock.Mock()
    comp.component_dir = tmp_path
    comp.environment_yml = tmp_path / "environment.yml"
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
    assert module_uses_dockerfile(comp)


def test_module_uses_dockerfile_in_parent_dir(tmp_path):
    """Dockerfile one level up (e.g. spaceranger/Dockerfile) is detected for submodules."""
    submodule_dir = tmp_path / "count"
    submodule_dir.mkdir()
    (tmp_path / "Dockerfile").write_text("FROM ubuntu:22.04\n")
    comp = mock.Mock()
    comp.component_dir = submodule_dir
    comp.environment_yml = None
    assert module_uses_dockerfile(comp)
