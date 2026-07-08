import logging
from pathlib import Path
from unittest import mock

import pytest
import yaml

from nf_core.modules.containers import ModuleContainers
from nf_core.modules.modules_utils import CondaEntry, ContainerEntry, MetaYmlContainers
from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS

from ..test_modules import TestModules


class TestModuleContainers(TestModules):
    """Tests for the ModuleContainers class"""

    def setUp(self):
        super().setUp()
        self.environment_yml = self.bpipe_test_module_path / "environment.yml"
        self.module_containers = ModuleContainers("bpipe/test", directory=self.nfcore_modules)

    def _write_meta(self, meta: dict) -> None:
        (self.bpipe_test_module_path / "meta.yml").write_text(yaml.safe_dump(meta), encoding="utf-8")

    def _containers_by_system(self, prefix: str = "testC") -> MetaYmlContainers:
        return MetaYmlContainers(
            docker={p: ContainerEntry(name=f"{prefix}-docker-{p}") for p in CONTAINER_PLATFORMS},
            singularity={p: ContainerEntry(name=f"{prefix}-singularity-{p}") for p in CONTAINER_PLATFORMS},
            conda={p: CondaEntry(lock_file=f"/path/to/{prefix}-{p}.txt") for p in CONTAINER_PLATFORMS},
        )

    def test_init_sets_paths(self):
        """Test that ModuleContainers initializes paths correctly"""
        assert self.module_containers.directory == Path(self.nfcore_modules)
        assert self.module_containers.module_directory == self.bpipe_test_module_path
        assert self.module_containers.environment_yml == self.bpipe_test_module_path / "environment.yml"
        assert self.module_containers.meta_yml == self.bpipe_test_module_path / "meta.yml"

    @staticmethod
    def _fake_response(payload: dict | None = None, status_code: int = 200, text: str = "") -> mock.MagicMock:
        """Build a fake requests.Response whose .json() returns ``payload``."""
        resp = mock.MagicMock()
        resp.status_code = status_code
        resp.text = text
        resp.json.return_value = payload or {}
        return resp

    @mock.patch("nf_core.modules.containers.requests.get")
    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.requests.post")
    def test_create_builds_containers(self, mock_post, mock_request_image_inspect, mock_requests_get):
        def fake_post(url, json=None, headers=None):
            # `format` is "sif" for singularity, "docker" otherwise
            system = "singularity" if json.get("format") == "sif" else "docker"
            image = "community.wave.seqera.io/library/bpipe_test:0.1.0--abc123"
            meta = {
                "buildId": f"bd-abc123-{system}",
                "cached": True,  # cached -> no status polling needed
                "containerImage": image,
                "freeze": True,
                "requestId": f"req-abc123-{system}",
                "succeeded": True,
                "targetImage": image,
            }
            if system == "docker":
                meta["scanId"] = f"sc-abc123-{system}"
            return self._fake_response(meta)

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

        # requests.get is used to download the conda lock file
        mock_requests_get.return_value = self._fake_response(text="# conda lock file content")

        mock_post.side_effect = fake_post
        mock_request_image_inspect.side_effect = fake_request_image_inspect

        containers, success = self.module_containers.create()
        assert self.module_containers.containers == containers
        assert success

        for system in CONTAINER_SYSTEMS:
            for platform in CONTAINER_PLATFORMS:
                entry = getattr(containers, system)[platform]
                assert entry.name == "community.wave.seqera.io/library/bpipe_test:0.1.0--abc123"
                assert entry.build_id == f"bd-abc123-{system}"
                if system == "docker":
                    assert entry.scan_id == f"sc-abc123-{system}"
                    platform_safe = platform.replace("/", "_")
                    build_id = f"bd-abc123-{system}"
                    expected_lock_path = str(
                        self.bpipe_test_module_path / ".conda-lock" / f"{platform_safe}-{build_id}.txt"
                    )
                    assert containers.conda[platform].lock_file == expected_lock_path
                else:
                    assert not entry.scan_id

    @mock.patch.object(ModuleContainers, "request_container")
    def test_create_skips_conda_lock_when_build_id_missing(self, mock_request_container):
        mock_request_container.return_value = ContainerEntry(name="bpipe_test-img")
        containers, success = self.module_containers.create()
        assert not containers.conda

    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_docker_success(self, mock_post):
        platform = CONTAINER_PLATFORMS[0]
        meta = {
            "targetImage": "testC:latest",
            "buildId": "build-1",
            "scanId": "scan-1",
            "cached": True,
        }
        mock_post.return_value = self._fake_response(meta)

        container = ModuleContainers.request_container("docker", platform, self.environment_yml)
        assert container.name == "testC:latest"
        assert container.build_id == "build-1"
        assert container.scan_id == "scan-1"

        # Inspect the submitted JSON payload instead of CLI args
        url = mock_post.call_args[0][0]
        payload = mock_post.call_args[1]["json"]
        assert url.endswith("/v1alpha2/container")
        assert payload["containerPlatform"] == platform
        assert payload["format"] == "docker"
        assert payload["freeze"] is True
        assert payload["nameStrategy"] == "imageSuffix"
        assert payload["packages"]["type"] == "CONDA"

    @mock.patch.object(ModuleContainers, "request_image_inspect")
    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_singularity_adds_https(self, mock_post, mock_request_image_inspect):
        platform = CONTAINER_PLATFORMS[0]
        meta = {"containerImage": "testC:sif", "buildId": "build-2", "cached": True}
        mock_post.return_value = self._fake_response(meta)
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

        container = ModuleContainers.request_container("singularity", platform, self.environment_yml)
        assert container.name == "testC:sif"
        assert mock_post.call_args[1]["json"]["format"] == "sif"
        expected_url = "https://community-cr-prod.seqera.io/docker/registry/v2/blobs/sha256/ab/abcde12345/data"
        assert container.https == expected_url
        mock_request_image_inspect.assert_called_once_with("testC:sif")

    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_submit_error_raises(self, mock_post):
        mock_post.return_value = self._fake_response(status_code=400, text="Bad Request")
        with pytest.raises(RuntimeError, match="Wave build submit .* failed: HTTP 400"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], self.environment_yml)

    @mock.patch("nf_core.modules.containers.requests.get")
    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_build_failure_raises(self, mock_post, mock_get):
        # Fresh (uncached) build -> polls the container status endpoint, which reports failure
        mock_post.return_value = self._fake_response(
            {"buildId": "bd-fail", "requestId": "req-fail", "cached": False, "targetImage": "x"}
        )
        mock_get.return_value = self._fake_response(
            {"status": "DONE", "succeeded": False, "reason": "boom", "detailsUri": "https://wave/log"}
        )
        with pytest.raises(RuntimeError, match="Wave build req-fail failed: boom"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], self.environment_yml)
        # Polled the v1alpha2 container status endpoint with the requestId
        assert mock_get.call_args[0][0].endswith("/v1alpha2/container/req-fail/status")

    @mock.patch("nf_core.modules.containers.requests.get")
    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_cached_failed_build_raises(self, mock_post, mock_get):
        # Wave reports a previously-failed build as cached/DONE but still returns a
        # targetImage. The submit-response success flag must be honoured so the failed
        # build is not silently recorded as a valid container.
        mock_post.return_value = self._fake_response(
            {
                "buildId": "bd-aa7e45b61425a0b2_7",
                "requestId": "req-cached",
                "cached": True,
                "status": "DONE",
                "succeeded": False,
                "reason": "arm64 build failed",
                "detailsUri": "https://wave/log",
                "targetImage": "community.wave.seqera.io/library/busco:6.1.0--aa7e45b61425a0b2",
            }
        )
        with pytest.raises(RuntimeError, match="Wave build bd-aa7e45b61425a0b2_7 failed: arm64 build failed"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], self.environment_yml)
        # A cached failure is resolved from the submit response alone - no status poll.
        mock_get.assert_not_called()

    @mock.patch("nf_core.modules.containers.requests.get")
    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_cached_without_result_polls_status(self, mock_post, mock_get):
        # Cached/DONE submit response with no explicit success flag -> fall back to the
        # authoritative status endpoint before accepting the image.
        mock_post.return_value = self._fake_response(
            {"buildId": "bd-cached", "requestId": "req-cached", "cached": True, "targetImage": "testC:latest"}
        )
        mock_get.return_value = self._fake_response({"status": "DONE", "succeeded": True})

        container = ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], self.environment_yml)
        assert container.name == "testC:latest"
        assert mock_get.call_args[0][0].endswith("/v1alpha2/container/req-cached/status")

    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_container_missing_image_raises(self, mock_post):
        mock_post.return_value = self._fake_response({"buildId": "build-4", "cached": True})
        with pytest.raises(RuntimeError, match="did not return an image name"):
            ModuleContainers.request_container("docker", CONTAINER_PLATFORMS[0], self.environment_yml)

    @mock.patch("nf_core.modules.containers.requests.post")
    def test_request_image_inspect_success(self, mock_post):
        inspect_payload = {"container": {"manifest": {"layers": []}}}
        mock_post.return_value = self._fake_response(inspect_payload)
        assert ModuleContainers.request_image_inspect("testC:latest") == inspect_payload
        assert mock_post.call_args[0][0].endswith("/v1alpha1/inspect")

    def test_get_conda_lock_url_quotes(self):
        build_id = "abc/def 123"
        url = ModuleContainers.get_conda_lock_url(build_id)
        assert "abc%2Fdef%20123" in url
        assert url.endswith("/condalock")

    @mock.patch("nf_core.modules.containers.requests.get")
    def test_get_conda_lock_file(self, mock_requests_get):
        """Test that get_conda_lock_file downloads from the correct URL"""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# conda lock file content"
        mock_requests_get.return_value = mock_response

        platform = CONTAINER_PLATFORMS[0]
        # Partial build state: fill the dicts directly, as create() does
        containers = MetaYmlContainers()
        containers.docker[platform] = ContainerEntry(name="placeholder", build_id="test-build-123")
        containers.conda[platform] = CondaEntry(lock_file="/some/path.txt")
        self.module_containers.containers = containers

        result = self.module_containers.get_conda_lock_file(platform)
        assert result == "# conda lock file content"
        expected_url = "https://wave.seqera.io/v1alpha1/builds/test-build-123/condalock"
        # The download now goes through wave_send, which passes json/headers too,
        # so assert on the URL rather than the full call signature.
        mock_requests_get.assert_called_once()
        assert mock_requests_get.call_args[0][0] == expected_url

    def test_list_containers(self):
        containers = self._containers_by_system("testC")
        with mock.patch.object(self.module_containers, "get_containers_from_meta", return_value=containers):
            listed = self.module_containers.list_containers()
        expected = []
        for cs in CONTAINER_SYSTEMS:
            for p in CONTAINER_PLATFORMS:
                expected.append((cs, p, getattr(containers, cs)[p].name))
        for p in CONTAINER_PLATFORMS:
            expected.append(("conda", p, containers.conda[p].lock_file))
        assert listed == expected

    def test_get_containers_from_meta_missing_section(self):
        self._write_meta({"name": "bpipe/test"})
        self.caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = self.module_containers.get_containers_from_meta()
        assert result is None
        assert "Section 'containers' missing from meta.yaml" in self.caplog.text

    def test_get_containers_from_meta_missing_system(self):
        singularity = {p: {"name": f"sif-{p}"} for p in CONTAINER_PLATFORMS}
        self._write_meta({"name": "bpipe/test", "containers": {"singularity": singularity}})
        self.caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = self.module_containers.get_containers_from_meta()
        assert result is None
        assert "No containers specified for docker" in self.caplog.text

    def test_get_containers_from_meta_optional_platform_missing_ok(self):
        """An optional platform (e.g. linux/arm64) may be absent - amd64 alone is valid."""
        containers = {
            "docker": {CONTAINER_PLATFORMS[0]: {"name": "img:1.0"}},
            "singularity": {CONTAINER_PLATFORMS[0]: {"name": "sif:1.0"}},
        }
        self._write_meta({"name": "bpipe/test", "containers": containers})
        result = self.module_containers.get_containers_from_meta()
        assert result is not None
        assert CONTAINER_PLATFORMS[0] in result.docker
        assert CONTAINER_PLATFORMS[1] not in result.docker

    def test_get_containers_from_meta_missing_required_platform(self):
        """A required platform (linux/amd64) must be present, or the section is invalid."""
        containers = {
            "docker": {CONTAINER_PLATFORMS[1]: {"name": "img:1.0"}},
            "singularity": {CONTAINER_PLATFORMS[1]: {"name": "sif:1.0"}},
        }
        self._write_meta({"name": "bpipe/test", "containers": containers})
        missing_platform = CONTAINER_PLATFORMS[0]
        self.caplog.set_level(logging.DEBUG, logger="nf_core.modules.containers")
        result = self.module_containers.get_containers_from_meta()
        assert result is None
        assert f"No docker entries found for expected platform: {missing_platform}" in self.caplog.text

    def test_get_containers_from_meta_partial_conda_ok(self):
        """A conda section missing some platforms (e.g. skipped lock files) must not invalidate the model."""
        containers = {
            "docker": {p: {"name": f"img-{p.replace('/', '-')}"} for p in CONTAINER_PLATFORMS},
            "singularity": {p: {"name": f"sif-{p.replace('/', '-')}"} for p in CONTAINER_PLATFORMS},
            "conda": {CONTAINER_PLATFORMS[0]: {"lock_file": "/lock/amd64.txt"}},
        }
        self._write_meta({"name": "bpipe/test", "containers": containers})
        result = self.module_containers.get_containers_from_meta()
        assert result is not None
        assert CONTAINER_PLATFORMS[0] in result.conda
        assert CONTAINER_PLATFORMS[1] not in result.conda

    def test_get_containers_from_meta_success(self):
        containers = {
            "docker": {
                platform: {"name": f"docker-image-{platform.replace('/', '-')}:latest"}
                for platform in CONTAINER_PLATFORMS
            },
            "singularity": {
                platform: {"name": f"singularity-image-{platform.replace('/', '-')}:latest"}
                for platform in CONTAINER_PLATFORMS
            },
        }
        self._write_meta({"name": "bpipe/test", "containers": containers})
        result = self.module_containers.get_containers_from_meta()
        assert result is not None
        assert result == MetaYmlContainers.model_validate(containers)

    def test_update_containers_in_meta_merges(self):
        self._write_meta({"name": "bpipe/test", "containers": {"docker": {"linux/amd64": {"name": "old"}}}})
        containers = self._containers_by_system("new")
        self.module_containers.containers = containers

        with mock.patch.object(self.module_containers, "create") as mock_create:
            self.module_containers.update_containers_in_meta()
            mock_create.assert_not_called()

        meta = yaml.safe_load((self.bpipe_test_module_path / "meta.yml").read_text(encoding="utf-8"))
        assert meta["containers"] == containers.dump_for_meta_yml()


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
        containers = MetaYmlContainers(
            docker={p: ContainerEntry(name=f"docker-{p}") for p in CONTAINER_PLATFORMS},
            singularity={p: ContainerEntry(name=f"sif-{p}") for p in CONTAINER_PLATFORMS},
            conda={p: CondaEntry(lock_file=f"/lock/{p}.txt") for p in CONTAINER_PLATFORMS},
        )
        manager.containers = containers

        with mock.patch.object(manager, "create") as mock_create:
            manager.update_containers_in_meta()
            mock_create.assert_not_called()

        meta = yaml.safe_load((module_dir / "meta.yml").read_text(encoding="utf-8"))
        assert meta["containers"] == containers.dump_for_meta_yml()


class TestModuleContainersDockerfile(TestModuleContainersPipeline):
    """Tests for ModuleContainers behaviour when a module uses a Dockerfile instead of environment.yml"""

    def setUp(self):
        super().setUp()
        module_dir = self.pipeline_dir / "modules" / "local" / "dockermod"
        module_dir.mkdir(parents=True, exist_ok=True)
        (module_dir / "Dockerfile").write_text("FROM ubuntu:22.04\n", encoding="utf-8")
        (module_dir / "meta.yml").write_text("name: dockermod\n", encoding="utf-8")
        (module_dir / "main.nf").write_text('container "my/image:latest"\n', encoding="utf-8")
        self.module_dir = module_dir
        self.module_containers = ModuleContainers("dockermod", directory=self.pipeline_dir)

    def test_create_returns_empty_for_dockerfile_module(self):
        containers, success = self.module_containers.create()
        assert containers == MetaYmlContainers()
        assert success

    def test_update_main_nf_container_skips_dockerfile_module(self):
        original = (self.module_dir / "main.nf").read_text()
        self.module_containers.update_main_nf_container()
        assert (self.module_dir / "main.nf").read_text() == original

    def test_update_containers_in_meta_skips_dockerfile_module(self):
        original_meta = (self.module_dir / "meta.yml").read_text()
        self.module_containers.update_containers_in_meta()
        assert (self.module_dir / "meta.yml").read_text() == original_meta
