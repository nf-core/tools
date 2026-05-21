import logging
from pathlib import Path
from unittest import mock

import pytest
import ruamel.yaml
import yaml

from nf_core import __version__
from nf_core.modules.containers import ModuleContainers
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS, NFCoreYamlConfig

from ..test_modules import TestModules


class TestModuleContainers:
    """Tests for the ModuleContainers class"""

    def _make_module(self, tmp_path: Path, module_name: str = "testC", with_env: bool = True):
        """
        Create a minimal module structure for testing.
        """
        module_dir = Path(tmp_path, "modules", "nf-core", module_name)
        module_dir.mkdir(parents=True, exist_ok=True)

        if with_env:
            (module_dir / "environment.yml").write_text(
                f"name: {module_name}\nchannels:\n  - defaults\ndependencies:\n  - python=3.11\n",
                encoding="utf-8",
            )

        (module_dir / "meta.yml").write_text(f"name: {module_name}\n", encoding="utf-8")
        (module_dir / "main.nf").write_text("", encoding="utf-8")
        return module_dir

    def _setup_modules_repo(self, tmp_path: Path, module_name: str = "testC", with_env: bool = True):
        """
        Create a full modules repo structure with a module in it.
        Returns (repo_root, module_dir).
        """
        import shutil

        # First create the module in a temporary location
        temp_module_dir = tmp_path / "temp_modules" / "nf-core" / module_name
        temp_module_dir.mkdir(parents=True, exist_ok=True)

        if with_env:
            (temp_module_dir / "environment.yml").write_text(
                f"name: {module_name}\nchannels:\n  - defaults\ndependencies:\n  - python=3.11\n",
                encoding="utf-8",
            )

        (temp_module_dir / "meta.yml").write_text(f"name: {module_name}\n", encoding="utf-8")
        (temp_module_dir / "main.nf").write_text("", encoding="utf-8")

        # Now create the actual repo structure
        repo_root = tmp_path / "modules_repo"
        repo_root.mkdir()
        (repo_root / "modules" / "nf-core").mkdir(parents=True)

        # Create .nf-core.yml so get_repo_info doesn't prompt
        _yaml = ruamel.yaml.YAML()
        nf_core_yml = NFCoreYamlConfig(nf_core_version=__version__, repository_type="modules", org_path="nf-core")
        with open(repo_root / ".nf-core.yml", "w") as fh:
            _yaml.dump(nf_core_yml.model_dump(), fh)

        # Create tests/config so nextflow config -flat succeeds during ModuleLint init
        (repo_root / "tests" / "config").mkdir(parents=True)
        (repo_root / "tests" / "config" / "nextflow.config").write_text("", encoding="utf-8")

        # Copy module to the repo
        shutil.copytree(temp_module_dir, repo_root / "modules" / "nf-core" / module_name)

        return repo_root, repo_root / "modules" / "nf-core" / module_name

    def _write_meta(self, module_dir: Path, meta: dict) -> None:
        (module_dir / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")

    def _containers_by_system(self, prefix: str = "testC") -> dict:
        return {
            "docker": {
                platform: {ModuleContainers.IMAGE_KEY: f"{prefix}-docker-{platform}"}
                for platform in CONTAINER_PLATFORMS
            },
            "singularity": {
                platform: {ModuleContainers.IMAGE_KEY: f"{prefix}-singularity-{platform}"}
                for platform in CONTAINER_PLATFORMS
            },
            "conda": {
                platform: {ModuleContainers.LOCK_FILE_KEY: f"/path/to/{prefix}-{platform}.txt"}
                for platform in CONTAINER_PLATFORMS
            },
        }

    def test_init_sets_paths(self, tmp_path: Path):
        """Test that ModuleContainers initializes paths correctly"""
        repo_root, module_dir = self._setup_modules_repo(tmp_path, module_name="testC")
        manager = ModuleContainers("testC", directory=repo_root)
        assert manager.directory == Path(repo_root)
        assert manager.module_directory == module_dir
        assert manager.environment_yml == module_dir / "environment.yml"
        assert manager.meta_yml == module_dir / "meta.yml"

    @mock.patch("nf_core.modules.containers.requests.get")
    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_create_builds_containers(
        self, mock_run_cmd, mock_request_image_inspect, mock_requests_get, tmp_path: Path
    ):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)

        def fake_run_cmd(executable: str, args_str: str):
            assert executable == "wave"
            system = "singularity" if "--singularity" in args_str else "docker"
            image = "community.wave.seqera.io/library/testC:0.1.0--abc123"
            build_id = f"bd-abc123-{system}"
            meta = {
                "buildId": build_id,
                "cached": True,
                "containerImage": image,
                "freeze": True,
                "mirror": False,
                "requestId": f"req-abc123-{system}",
                "scanId": f"sc-abc123-{system}" if system == "docker" else None,
                "succeeded": True,
                "targetImage": image,
            }
            meta = {k: v for k, v in meta.items() if v is not None}
            return (yaml.safe_dump(meta).encode(), b"")

        def fake_request_image_inspect(image: str):
            return {
                "container": {
                    "manifest": {
                        "layers": [
                            {
                                "mediaType": "application/vnd.sif",
                                "digest": "sha256:abcde12345",
                            }
                        ]
                    }
                }
            }

        # Mock requests.get for conda lock file download
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# conda lock file content"
        mock_requests_get.return_value = mock_response

        mock_run_cmd.side_effect = fake_run_cmd
        mock_request_image_inspect.side_effect = fake_request_image_inspect

        manager = ModuleContainers("testC", directory=repo_root)
        containers, success = manager.create(await_build=True)
        assert manager.containers == containers
        assert success

        for system in CONTAINER_SYSTEMS:
            for platform in CONTAINER_PLATFORMS:
                entry = containers[system][platform]
                assert entry[ModuleContainers.IMAGE_KEY] == "community.wave.seqera.io/library/testC:0.1.0--abc123"
                assert entry[ModuleContainers.BUILD_ID_KEY] == f"bd-abc123-{system}"
                if system == "docker":
                    assert entry[ModuleContainers.SCAN_ID_KEY] == f"sc-abc123-{system}"
                    # Check that conda lock file path exists and is correct
                    platform_safe = platform.replace("/", "_")
                    build_id = f"bd-abc123-{system}"
                    expected_lock_path = str(module_dir / ".conda-lock" / f"{platform_safe}-{build_id}.txt")
                    assert containers["conda"][platform][ModuleContainers.LOCK_FILE_KEY] == expected_lock_path
                else:
                    assert ModuleContainers.SCAN_ID_KEY not in entry

    @mock.patch.object(ModuleContainers, "request_container")
    def test_create_skips_conda_lock_when_build_id_missing(self, mock_request_container, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        mock_request_container.return_value = {ModuleContainers.IMAGE_KEY: "testC-img"}

        manager = ModuleContainers("testC", directory=repo_root)
        containers = manager.create()
        assert "conda" not in containers

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_docker_success(self, mock_run_cmd, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        platform = CONTAINER_PLATFORMS[0]
        meta = {"targetImage": "testC:latest", "buildId": "build-1", "scanId": "scan-1", "succeeded": True}
        mock_run_cmd.return_value = (yaml.safe_dump(meta).encode(), b"")

        container = ModuleContainers.request_container("docker", platform, conda_file, await_build=True)
        assert container[ModuleContainers.IMAGE_KEY] == "testC:latest"
        assert container[ModuleContainers.BUILD_ID_KEY] == "build-1"
        assert container[ModuleContainers.SCAN_ID_KEY] == "scan-1"

        args_str = mock_run_cmd.call_args[0][1]
        assert "--await" in args_str
        assert "--platform" in args_str
        assert platform in args_str
        assert "--singularity" not in args_str

    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_singularity_adds_https(self, mock_run_cmd, mock_request_image_inspect, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        platform = CONTAINER_PLATFORMS[0]
        meta = {"containerImage": "testC:sif", "buildId": "build-2", "succeeded": True}
        mock_run_cmd.return_value = (yaml.safe_dump(meta).encode(), b"")
        mock_request_image_inspect.return_value = {
            "container": {
                "manifest": {
                    "layers": [
                        {
                            "mediaType": "application/vnd.sif",
                            "digest": "sha256:abcde12345",
                        }
                    ]
                }
            }
        }

        container = ModuleContainers.request_container("singularity", platform, conda_file, await_build=True)
        assert container[ModuleContainers.IMAGE_KEY] == "testC:sif"
        expected_url = "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/ab/abcde12345/data"
        assert container[ModuleContainers.HTTPS_URL_KEY] == expected_url
        mock_request_image_inspect.assert_called_once_with("testC:sif")

    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_singularity_no_await_does_not_inspect(
        self, mock_run_cmd, mock_request_image_inspect, tmp_path: Path
    ):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        platform = CONTAINER_PLATFORMS[0]
        meta = {"containerImage": "testC:sif", "buildId": "build-3", "succeeded": True}
        mock_run_cmd.return_value = (yaml.safe_dump(meta).encode(), b"")

        container = ModuleContainers.request_container("singularity", platform, conda_file, await_build=False)
        assert "https" not in container
        mock_request_image_inspect.assert_not_called()

    @mock.patch("nf_core.modules.containers.run_cmd", return_value=None)
    def test_request_container_missing_output_raises(self, mock_run_cmd, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        with pytest.raises(RuntimeError, match="Wave command did not return any output"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], conda_file)

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_invalid_yaml_raises(self, mock_run_cmd, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        mock_run_cmd.return_value = (b"invalid: [", b"")
        with pytest.raises(RuntimeError, match="Could not parse wave YAML metadata"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], conda_file)

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_missing_image_raises(self, mock_run_cmd, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        meta = {"buildId": "build-4", "succeeded": True}
        mock_run_cmd.return_value = (yaml.safe_dump(meta).encode(), b"")
        with pytest.raises(RuntimeError, match="did not return an image name"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], conda_file)

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_image_inspect_success(self, mock_run_cmd):
        inspect_payload = {"container": {"manifest": {"layers": []}}}
        mock_run_cmd.return_value = (yaml.safe_dump(inspect_payload).encode(), b"")
        assert ModuleContainers.request_image_inspect("testC:latest") == inspect_payload

    @mock.patch("nf_core.modules.containers.run_cmd", return_value=None)
    def test_request_image_inspect_missing_output(self, mock_run_cmd):
        with pytest.raises(RuntimeError, match="Wave command did not return any output"):
            ModuleContainers.request_image_inspect("testC:latest")

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_image_inspect_invalid_yaml(self, mock_run_cmd):
        mock_run_cmd.return_value = (b"invalid: [", b"")
        with pytest.raises(RuntimeError, match="Could not parse wave inspect yaml output"):
            ModuleContainers.request_image_inspect("testC:latest")

    def test_get_conda_lock_url_quotes(self):
        build_id = "abc/def 123"
        url = ModuleContainers.get_conda_lock_url(build_id)
        assert "abc%2Fdef%20123" in url
        assert url.endswith("/condalock")

    @mock.patch("nf_core.modules.containers.requests.get")
    def test_get_conda_lock_file(self, mock_requests_get, tmp_path: Path):
        """Test that get_conda_lock_file downloads from the correct URL"""
        repo_root, module_dir = self._setup_modules_repo(tmp_path)

        # Set up mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# conda lock file content"
        mock_requests_get.return_value = mock_response

        # Create containers with build_id in docker container
        manager = ModuleContainers("testC", directory=repo_root)
        platform = CONTAINER_PLATFORMS[0]
        manager.containers = {
            "docker": {platform: {ModuleContainers.BUILD_ID_KEY: "test-build-123"}},
            "conda": {platform: {"lock_file": "/some/path.txt"}},
        }

        result = manager.get_conda_lock_file(platform)
        assert result == "# conda lock file content"
        # Verify it generated the correct URL from the build_id
        expected_url = "https://wave.seqera.io/v1alpha1/builds/test-build-123/condalock"
        mock_requests_get.assert_called_once_with(expected_url)

    def test_list_containers(self, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        manager = ModuleContainers("testC", directory=repo_root)
        containers = self._containers_by_system("testC")
        with mock.patch.object(manager, "get_containers_from_meta", return_value=containers):
            listed = manager.list_containers()
        # Build expected list including docker, singularity, and conda
        expected = []
        for cs in CONTAINER_SYSTEMS:
            for p in CONTAINER_PLATFORMS:
                expected.append((cs, p, containers[cs][p][ModuleContainers.IMAGE_KEY]))
        for p in CONTAINER_PLATFORMS:
            expected.append(("conda", p, containers["conda"][p][ModuleContainers.LOCK_FILE_KEY]))
        assert listed == expected

    def test_get_containers_from_meta_missing_section(self, tmp_path: Path, caplog):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        self._write_meta(module_dir, {"name": "testC"})
        manager = ModuleContainers("testC", directory=repo_root)

        caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = manager.get_containers_from_meta()
        assert result == {}
        assert "Section 'containers' missing from meta.yaml" in caplog.text

    def test_get_containers_from_meta_missing_system(self, tmp_path: Path, caplog):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        self._write_meta(module_dir, {"name": "testC", "containers": {"singularity": {"ok": True}}})
        manager = ModuleContainers("testC", directory=repo_root)
        caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = manager.get_containers_from_meta()
        assert result == {}
        assert "Container missing for docker" in caplog.text

    def test_get_containers_from_meta_missing_platform_key(self, tmp_path: Path, caplog):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        # Only include one platform under docker/singularity, missing the other
        containers = {
            "docker": {CONTAINER_PLATFORMS[0]: {"ok": True}},
            "singularity": {CONTAINER_PLATFORMS[0]: {"ok": True}},
        }
        self._write_meta(module_dir, {"name": "testC", "containers": containers})
        manager = ModuleContainers("testC", directory=repo_root)
        missing_platform = CONTAINER_PLATFORMS[1]
        caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = manager.get_containers_from_meta()
        assert result == {}
        assert f"Platform build {missing_platform} missing" in caplog.text

    def test_get_containers_from_meta_success(self, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        containers = {
            "docker": {platform: {"ok": True} for platform in CONTAINER_PLATFORMS},
            "singularity": {platform: {"ok": True} for platform in CONTAINER_PLATFORMS},
        }
        self._write_meta(module_dir, {"name": "testC", "containers": containers})
        manager = ModuleContainers("testC", directory=repo_root)
        assert manager.get_containers_from_meta() == containers

    def test_update_containers_in_meta_merges(self, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        self._write_meta(module_dir, {"name": "testC", "containers": {"docker": {"linux/amd64": {"name": "old"}}}})
        manager = ModuleContainers("testC", directory=repo_root)
        containers = self._containers_by_system("new")
        manager.containers = containers

        with mock.patch.object(manager, "create") as mock_create:
            manager.update_containers_in_meta()
            mock_create.assert_not_called()

        meta = yaml.safe_load((module_dir / "meta.yml").read_text(encoding="utf-8"))
        assert meta["containers"] == containers


class TestModuleContainersPipeline(TestModules):
    """Tests for ModuleContainers against a real pipeline repository"""

    def _create_local_module(self, module_name: str = "testmodule") -> Path:
        """Create a minimal local module under pipeline's modules/local/."""
        module_dir = self.pipeline_dir / "modules" / "local" / module_name
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "environment.yml").write_text(
            f"name: {module_name}\nchannels:\n  - defaults\ndependencies:\n  - python=3.11\n",
            encoding="utf-8",
        )
        (module_dir / "meta.yml").write_text(f"name: {module_name}\n", encoding="utf-8")
        (module_dir / "main.nf").write_text("", encoding="utf-8")
        return module_dir

    def test_init_pipeline_sets_local_module_paths(self):
        """ModuleContainers should resolve paths into modules/local/ for a pipeline repo"""
        module_dir = self._create_local_module("testmodule")
        manager = ModuleContainers("testmodule", directory=self.pipeline_dir)

        assert manager.repo_type == "pipeline"
        assert manager.module_directory == module_dir
        assert manager.environment_yml == module_dir / "environment.yml"
        assert manager.meta_yml == module_dir / "meta.yml"

    def test_update_containers_in_meta_pipeline(self):
        """update_containers_in_meta writes containers to the local module's meta.yml"""
        module_dir = self._create_local_module("testmodule")

        manager = ModuleContainers("testmodule", directory=self.pipeline_dir)
        containers = {
            "docker": {p: {ModuleContainers.IMAGE_KEY: f"docker-{p}"} for p in CONTAINER_PLATFORMS},
            "singularity": {p: {ModuleContainers.IMAGE_KEY: f"sif-{p}"} for p in CONTAINER_PLATFORMS},
            "conda": {p: {ModuleContainers.LOCK_FILE_KEY: f"/lock/{p}.txt"} for p in CONTAINER_PLATFORMS},
        }
        manager.containers = containers

        with mock.patch.object(manager, "create") as mock_create:
            manager.update_containers_in_meta()
            mock_create.assert_not_called()

        meta = yaml.safe_load((module_dir / "meta.yml").read_text(encoding="utf-8"))
        assert meta["containers"] == containers
