import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
import ruamel.yaml

import nf_core.modules.bump_versions
from nf_core import __version__
from nf_core.modules.containers import ModuleContainers
from nf_core.modules.modules_utils import MetaYmlContainers, ModuleExceptionError
from nf_core.utils import NFCoreYamlConfig

from ..test_modules import TestModules


class TestModulesBumpVersions(TestModules):
    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    def test_modules_bump_versions_single_module(self, mock_build):
        """Test updating a single module"""
        # Change the bpipe/test version to an older version
        env_yml_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")
        with open(env_yml_path) as fh:
            content = fh.read()
        new_content = re.sub(r"bioconda::star=\d.\d.\d\D?", r"bioconda::star=2.6.1d", content)
        with open(env_yml_path, "w") as fh:
            fh.write(new_content)
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        # mock_build keeps the Wave container rebuild from shelling out to the `wave` CLI
        modules = version_bumper.bump_versions(module="bpipe/test")
        assert len(version_bumper.failed) == 0
        assert [m.component_name for m in modules] == ["bpipe/test"]

    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    def test_modules_bump_versions_all_modules(self, mock_build):
        """Test updating all modules"""
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        modules = version_bumper.bump_versions(all_modules=True)
        assert len(version_bumper.failed) == 0
        assert [m.component_name for m in modules] == ["bpipe/test"]

    @mock.patch.object(ModuleContainers, "create", return_value=(MetaYmlContainers(), False))
    def test_build_wave_containers(self, mock_create):
        """Test building Wave containers and recording failed modules."""
        module_containers = ModuleContainers("bpipe/test", directory=self.nfcore_modules)
        module = module_containers.nfcore_component
        assert module is not None
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)

        with mock.patch.dict("os.environ", {"TOWER_ACCESS_TOKEN": ""}):
            version_bumper._build_wave_containers([module])

        # ModuleContainers and its batch progress logic are real; only the external build is mocked.
        mock_create.assert_called_once()
        assert "TOWER_ACCESS_TOKEN is not set" in self.caplog.text
        assert version_bumper.failed == [("Container build with Wave failed", "bpipe/test")]

    @staticmethod
    def _mock_nf_core_yml(root_dir: Path) -> None:
        """Mock the .nf_core.yml"""
        yaml = ruamel.yaml.YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)
        nf_core_yml = NFCoreYamlConfig(nf_core_version=__version__, repository_type="modules", org_path="nf-core")
        with open(Path(root_dir, ".nf-core.yml"), "w") as fh:
            yaml.dump(nf_core_yml.model_dump(), fh)

    @staticmethod
    def _mock_modules(root_dir: Path, modules: list[str]) -> None:
        """Mock the directory for a given module (or sub-module) for use with `dry_run`"""
        nf_core_dir = root_dir / "modules" / "nf-core"
        for module in modules:
            if "/" in module:
                module, sub_module = module.split("/")
                module_dir = nf_core_dir / module / sub_module
            else:
                module_dir = nf_core_dir / module
            module_dir.mkdir(parents=True)
            module_main = module_dir / "main.nf"
            with module_main.open("w"):
                pass

    def test_modules_bump_versions_multiple_modules(self):
        """Test updating all modules when multiple modules are present"""
        # mock the fgbio directory
        root_dir = Path(tempfile.TemporaryDirectory().name)
        self._mock_modules(root_dir=root_dir, modules=["fqgrep", "fqtk"])
        # mock the ".nf-core.yml"
        self._mock_nf_core_yml(root_dir=root_dir)

        # run it with dryrun to return the modules that it found
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=root_dir)
        modules = version_bumper.bump_versions(all_modules=True, dry_run=True)
        assert sorted([m.component_name for m in modules]) == sorted(["fqgrep", "fqtk"])

    def test_modules_bump_versions_submodules(self):
        """Test updating a submodules"""
        # mock the fgbio directory
        root_dir = Path(tempfile.TemporaryDirectory().name)
        in_modules = ["fgbio/callduplexconsensusreads", "fgbio/groupreadsbyumi"]
        self._mock_modules(root_dir=root_dir, modules=in_modules)
        # mock the ".nf-core.yml"
        self._mock_nf_core_yml(root_dir=root_dir)

        # run it with dryrun to return the modules that it found
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=root_dir)
        out_modules = version_bumper.bump_versions(module="fgbio", dry_run=True)
        assert sorted([m.component_name for m in out_modules]) == sorted(in_modules)

    def test_containers_built_for_version(self):
        """Check-2: detect whether a module's conda locks already pin the current version."""
        # Bypass __init__ - the method only uses the passed module's component_dir
        bumper = nf_core.modules.bump_versions.ModuleVersionBumper.__new__(
            nf_core.modules.bump_versions.ModuleVersionBumper
        )
        mod_dir = Path(tempfile.mkdtemp())
        meta_yml = mod_dir / "meta.yml"
        module = SimpleNamespace(component_dir=mod_dir, component_name="samtools/sort", meta_yml=meta_yml)

        # No .conda-lock dir at all -> not Wave-managed, treated as up to date (no rebuild)
        assert bumper._containers_built_for_version(module, "samtools", "1.21") is True

        lock_dir = mod_dir / ".conda-lock"
        lock_dir.mkdir()
        # Empty .conda-lock dir -> a Wave build was started but interrupted before writing locks
        assert bumper._containers_built_for_version(module, "samtools", "1.21") is False

        (lock_dir / "linux_amd64-bd-abc_1.txt").write_text(
            "- conda: https://conda.anaconda.org/bioconda/noarch/samtools-1.21-h50ea8bc_0.conda\n"
        )
        # Lock current but meta.yml missing its containers section (build interrupted before the
        # final meta.yml write) -> rebuild
        meta_yml.write_text("name: samtools_sort\n")
        assert bumper._containers_built_for_version(module, "samtools", "1.21") is False

        # Lock current AND meta.yml carries a containers section -> already built, no rebuild
        meta_yml.write_text("name: samtools_sort\ncontainers:\n  docker:\n    linux/amd64:\n      name: img\n")
        assert bumper._containers_built_for_version(module, "samtools", "1.21") is True
        # Trailing dash anchors the match so 1.21 does not also match 1.210
        assert bumper._containers_built_for_version(module, "samtools", "1.2") is False
        # Lock pins an older version (e.g. interrupted build left stale locks) -> rebuild
        assert bumper._containers_built_for_version(module, "samtools", "1.22") is False

    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    @mock.patch("nf_core.utils.anaconda_package")
    def test_modules_bump_versions_stale_containers_rebuild(self, mock_anaconda, mock_build):
        """Check-2 integration: version is current but the conda locks are stale -> rebuild queued.

        Mirrors an earlier run that bumped environment.yml but was interrupted before the Wave
        build finished, leaving conda locks pinned to the previous version.
        """
        # bpipe/test pins bioconda::bpipe=0.9.13; report that as the latest so check-1 is a no-op
        mock_anaconda.return_value = {"versions": ["0.9.13"], "latest_version": "0.9.13"}

        # Leave behind a stale conda lock (older version) for the module
        lock_dir = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", ".conda-lock")
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "linux_amd64-bd-stale_1.txt").write_text(
            "- conda: https://conda.anaconda.org/bioconda/noarch/bpipe-0.9.12-hdfd78af_0.conda\n"
        )

        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        version_bumper.bump_versions(module="bpipe/test")

        assert len(version_bumper.failed) == 0
        mock_build.assert_called_once()
        assert [m.component_name for m in mock_build.call_args.args[0]] == ["bpipe/test"]
        assert any("Containers out of date" in msg for msg, _ in version_bumper.updated)

    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    @mock.patch("nf_core.utils.anaconda_package")
    def test_modules_bump_versions_interrupted_build_rebuild(self, mock_anaconda, mock_build):
        """Check-2 integration: version current, empty .conda-lock dir (interrupted build) -> rebuild."""
        mock_anaconda.return_value = {"versions": ["0.9.13"], "latest_version": "0.9.13"}

        # An interrupted build created the .conda-lock dir but wrote no locks
        lock_dir = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", ".conda-lock")
        lock_dir.mkdir(parents=True, exist_ok=True)

        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        version_bumper.bump_versions(module="bpipe/test")

        assert len(version_bumper.failed) == 0
        mock_build.assert_called_once()
        assert [m.component_name for m in mock_build.call_args.args[0]] == ["bpipe/test"]

    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    @mock.patch("nf_core.utils.anaconda_package")
    def test_modules_bump_versions_missing_meta_containers_rebuild(self, mock_anaconda, mock_build):
        """Check-2 integration: locks current but meta.yml has no containers section -> rebuild.

        Mirrors a build interrupted after writing the conda locks but before meta.yml/main.nf.
        """
        mock_anaconda.return_value = {"versions": ["0.9.13"], "latest_version": "0.9.13"}

        module_dir = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test")
        # Current-version lock present...
        lock_dir = module_dir / ".conda-lock"
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "linux_amd64-bd-current_1.txt").write_text(
            "- conda: https://conda.anaconda.org/bioconda/noarch/bpipe-0.9.13-hdfd78af_0.conda\n"
        )
        # ...but the containers section never got written (build interrupted before meta.yml)
        meta_path = module_dir / "meta.yml"
        yaml = ruamel.yaml.YAML()
        with open(meta_path) as fh:
            meta = yaml.load(fh)
        meta.pop("containers", None)
        with open(meta_path, "w") as fh:
            yaml.dump(meta, fh)

        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        version_bumper.bump_versions(module="bpipe/test")

        assert len(version_bumper.failed) == 0
        mock_build.assert_called_once()
        assert [m.component_name for m in mock_build.call_args.args[0]] == ["bpipe/test"]

    @mock.patch.object(nf_core.modules.bump_versions.ModuleVersionBumper, "_build_wave_containers")
    @mock.patch("nf_core.utils.anaconda_package")
    def test_modules_bump_versions_current_containers_no_rebuild(self, mock_anaconda, mock_build):
        """Check-2 integration: version current, locks match AND meta has containers -> no rebuild."""
        mock_anaconda.return_value = {"versions": ["0.9.13"], "latest_version": "0.9.13"}

        module_dir = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test")
        # Conda lock already pins the current version
        lock_dir = module_dir / ".conda-lock"
        lock_dir.mkdir(parents=True, exist_ok=True)
        (lock_dir / "linux_amd64-bd-current_1.txt").write_text(
            "- conda: https://conda.anaconda.org/bioconda/noarch/bpipe-0.9.13-hdfd78af_0.conda\n"
        )
        # ...and meta.yml carries a containers section, so the build is considered complete
        meta_path = module_dir / "meta.yml"
        yaml = ruamel.yaml.YAML()
        with open(meta_path) as fh:
            meta = yaml.load(fh)
        meta["containers"] = {"docker": {"linux/amd64": {"name": "img"}}}
        with open(meta_path, "w") as fh:
            yaml.dump(meta, fh)

        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        version_bumper.bump_versions(module="bpipe/test")

        assert len(version_bumper.failed) == 0
        mock_build.assert_not_called()
        assert any("up to date" in msg for msg, _ in version_bumper.up_to_date)

    @mock.patch("nf_core.utils.anaconda_package")
    def test_modules_bump_versions_multi_package(self, mock_anaconda):
        """Multi-package ('mulled') modules are now bumped, not skipped, and YAML comments survive."""
        mock_anaconda.return_value = {"versions": ["1.21", "1.23.1"], "latest_version": "1.23.1"}

        mod_dir = Path(tempfile.mkdtemp())
        env_yml = mod_dir / "environment.yml"
        env_yml.write_text(
            "channels:\n"
            "  - conda-forge\n"
            "  - bioconda\n"
            "dependencies:\n"
            "  # renovate: datasource=conda depName=bioconda/htslib\n"
            "  - bioconda::htslib=1.21\n"
            "  # renovate: datasource=conda depName=bioconda/samtools\n"
            "  - bioconda::samtools=1.21\n"
        )

        # Bypass __init__ - bump_module_version only needs the result lists, tools_config and directory
        bumper = nf_core.modules.bump_versions.ModuleVersionBumper.__new__(
            nf_core.modules.bump_versions.ModuleVersionBumper
        )
        bumper.failed = []
        bumper.ignored = []
        bumper.updated = []
        bumper.up_to_date = []
        bumper.directory = mod_dir
        bumper.tools_config = SimpleNamespace()
        module = SimpleNamespace(
            component_name="samtools/cat",
            component_dir=mod_dir,
            environment_yml=env_yml,
            meta_yml=None,
        )

        assert bumper.bump_module_version(module) is True
        assert bumper.failed == []
        assert len(bumper.updated) == 2

        new_content = env_yml.read_text()
        # Both bioconda packages were bumped...
        assert "bioconda::htslib=1.23.1" in new_content
        assert "bioconda::samtools=1.23.1" in new_content
        # ...and the renovate comments were preserved (no yaml round-trip)
        assert "# renovate: datasource=conda depName=bioconda/htslib" in new_content
        assert "# renovate: datasource=conda depName=bioconda/samtools" in new_content

    def test_modules_bump_versions_fail(self):
        """Fail updating a module with wrong name"""
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        with pytest.raises(ModuleExceptionError) as excinfo:
            version_bumper.bump_versions(module="no/module")
        assert "Could not find the specified module:" in str(excinfo.value)

    def test_modules_bump_versions_fail_unknown_version(self):
        """Fail because of an unknown version"""
        # Change the bpipe/test version to an older version
        env_yml_path = Path(self.nfcore_modules, "modules", "nf-core", "bpipe", "test", "environment.yml")
        with open(env_yml_path) as fh:
            content = fh.read()
        new_content = re.sub(r"bioconda::bpipe=\d.\d.\d\D?", r"bioconda::bpipe=xxx", content)
        with open(env_yml_path, "w") as fh:
            fh.write(new_content)
        version_bumper = nf_core.modules.bump_versions.ModuleVersionBumper(pipeline_dir=self.nfcore_modules)
        version_bumper.bump_versions(module="bpipe/test")
        assert "Conda package had unknown version" in version_bumper.failed[0][0]
