import logging
from pathlib import Path
from unittest import mock

import pytest
import yaml

from nf_core.modules.containers import ModuleContainers
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS


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

        # Copy module to the repo
        shutil.copytree(temp_module_dir, repo_root / "modules" / "nf-core" / module_name)

        return repo_root, repo_root / "modules" / "nf-core" / module_name

    def _write_meta(self, module_dir: Path, meta: dict) -> None:
        (module_dir / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")

    def _containers_by_system(self, prefix: str = "testC") -> dict:
        return {
            "docker": {platform: {"name": f"{prefix}-docker-{platform}"} for platform in CONTAINER_PLATFORMS},
            "singularity": {platform: {"name": f"{prefix}-singularity-{platform}"} for platform in CONTAINER_PLATFORMS},
        }

    def test_init_sets_paths(self, tmp_path: Path):
        """Test that ModuleContainers initializes paths correctly"""
        repo_root, module_dir = self._setup_modules_repo(tmp_path, module_name="testC")
        manager = ModuleContainers("testC", directory=repo_root)
        assert manager.directory == Path(repo_root)
        assert manager.module_directory == module_dir
        assert manager.environment_yml == module_dir / "environment.yml"
        assert manager.meta_yml == module_dir / "meta.yml"

    def test_get_meta_returns_dict(self, tmp_path: Path):
        """Test that get_meta returns the meta.yml content"""
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        meta = {"name": "testC", "foo": {"bar": "baz"}}
        self._write_meta(module_dir, meta)
        manager = ModuleContainers("testC", directory=repo_root)
        assert manager.get_meta() == meta

    @mock.patch.object(ModuleContainers, "request_conda_lock_file")
    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_create_builds_containers(
        self, mock_run_cmd, mock_request_image_inspect, mock_request_conda_lock, tmp_path: Path
    ):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)

        def fake_run_cmd(executable: str, args_str: str):
            assert executable == "wave"
            platform = next(p for p in CONTAINER_PLATFORMS if p in args_str)
            system = "singularity" if "--singularity" in args_str else "docker"
            image = f"community.wave.seqera.io/library/testC-{system}:{platform.replace('/', '-')}"
            build_id = f"bd-{system}-{platform}-build"
            meta = {
                "buildId": build_id,
                "cached": True,
                "containerImage": image,
                "freeze": True,
                "mirror": False,
                "requestId": f"req-{system}-{platform}",
                "scanId": f"sc-{system}-{platform}-scan" if system == "docker" else None,
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

        mock_run_cmd.side_effect = fake_run_cmd
        mock_request_image_inspect.side_effect = fake_request_image_inspect
        mock_request_conda_lock.return_value = "# conda lock file content"

        manager = ModuleContainers("testC", directory=repo_root)
        containers, success = manager.create(await_build=True)
        assert manager.containers == containers
        assert success is True

        for system in CONTAINER_SYSTEMS:
            for platform in CONTAINER_PLATFORMS:
                entry = containers[system][platform]
                expected_image = f"community.wave.seqera.io/library/testC-{system}:{platform.replace('/', '-')}"
                assert entry["name"] == expected_image
                assert entry["buildId"] == f"bd-{system}-{platform}-build"
                if system == "docker":
                    assert entry["scanId"] == f"sc-{system}-{platform}-scan"
                    # Check that conda lock file path exists and is correct
                    platform_safe = platform.replace("/", "-")
                    build_id = f"bd-{system}-{platform}-build"
                    expected_lock_path = str(module_dir / ".conda-lock" / f"{platform_safe}-{build_id}.txt")
                    assert containers["conda"][platform]["lock_file"] == expected_lock_path
                else:
                    assert "scanId" not in entry

    @mock.patch.object(ModuleContainers, "request_container")
    def test_create_skips_conda_lock_when_build_id_missing(self, mock_request_container, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        mock_request_container.return_value = {"name": "testC-img"}

        manager = ModuleContainers("testC", directory=repo_root)
        containers = manager.create()
        assert "conda" not in containers

    @mock.patch("nf_core.modules.containers.run_cmd", return_value=None)
    def test_create_raises_on_missing_wave_output(self, mock_run_cmd, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        manager = ModuleContainers("testC", directory=repo_root)
        with pytest.raises(RuntimeError, match="Wave command did not return any output"):
            manager.create(await_build=True)

    @mock.patch("nf_core.modules.containers.run_cmd")
    def test_request_container_docker_success(self, mock_run_cmd, tmp_path: Path):
        module_dir = self._make_module(tmp_path)
        conda_file = module_dir / "environment.yml"
        platform = CONTAINER_PLATFORMS[0]
        meta = {"targetImage": "testC:latest", "buildId": "build-1", "scanId": "scan-1", "succeeded": True}
        mock_run_cmd.return_value = (yaml.safe_dump(meta).encode(), b"")

        container = ModuleContainers.request_container("docker", platform, conda_file, await_build=True)
        assert container["name"] == "testC:latest"
        assert container["buildId"] == "build-1"
        assert container["scanId"] == "scan-1"

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
        assert container["name"] == "testC:sif"
        expected_url = "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/ab/abcde12345/data"
        assert container["https"] == expected_url
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

    def test_request_conda_lock_file(self):
        # TODO
        pass

    def test_list_containers(self, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        manager = ModuleContainers("testC", directory=repo_root)
        containers = self._containers_by_system("testC")
        with mock.patch.object(manager, "get_containers_from_meta", return_value=containers):
            listed = manager.list_containers()
        expected = [(cs, p, containers[cs][p]["name"]) for cs in CONTAINER_SYSTEMS for p in CONTAINER_PLATFORMS]
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
        containers = {"docker": {"ok": True}, "singularity": {"ok": True}, CONTAINER_PLATFORMS[0]: {"ok": True}}
        self._write_meta(module_dir, {"name": "testC", "containers": containers})
        manager = ModuleContainers("testC", directory=repo_root)
        missing_platform = CONTAINER_PLATFORMS[1]
        caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = manager.get_containers_from_meta()
        assert result == {}
        assert f"Platform build {missing_platform} missing" in caplog.text

    def test_get_containers_from_meta_success(self, tmp_path: Path):
        repo_root, module_dir = self._setup_modules_repo(tmp_path)
        containers = {"docker": {"ok": True}, "singularity": {"ok": True}}
        for platform in CONTAINER_PLATFORMS:
            containers[platform] = {"ok": True}
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
