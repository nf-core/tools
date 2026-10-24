"""Focused Wave request-contract regressions, independent of Nextflow fixtures."""

import base64
from unittest import mock

import pytest

from nf_core.modules.containers import ModuleContainers
from nf_core.utils import CONTAINER_PLATFORMS


@pytest.mark.parametrize("container_system,expected_format", [("docker", "docker"), ("singularity", "sif")])
def test_request_container_nests_pixi_base_packages_for_all_formats(tmp_path, container_system, expected_format):
    environment = tmp_path / "environment.yml"
    environment.write_text("dependencies:\n  - gzip=1.13\n")
    result = {"targetImage": "example:test", "buildId": "test-123", "cached": True, "succeeded": True}

    with (
        mock.patch.object(ModuleContainers, "_build_cache", {}),
        mock.patch("nf_core.modules.containers.wave_request", return_value=result) as request,
        mock.patch.object(
            ModuleContainers, "request_image_inspect", return_value={"container": {"manifest": {"layers": []}}}
        ),
    ):
        container = ModuleContainers.request_container(container_system, CONTAINER_PLATFORMS[0], environment)

    assert container.name == "example:test"
    request.assert_called_once()
    method, url, payload = request.call_args.args
    assert method == "post"
    assert url.endswith("/v1alpha2/container")
    assert payload["format"] == expected_format
    assert payload["buildTemplate"] == "conda/pixi:v1"
    assert payload["packages"]["type"] == "CONDA"
    assert base64.b64decode(payload["packages"]["environment"]) == environment.read_bytes()
    assert payload["packages"]["pixiOpts"] == {"basePackages": "conda-forge::procps conda-forge::gzip"}
    assert "basePackages" not in payload
