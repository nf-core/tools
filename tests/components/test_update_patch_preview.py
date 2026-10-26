from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from nf_core.components.update import ComponentUpdate


@pytest.mark.parametrize("nested", [False, True])
def test_failed_patch_preview_keeps_original_file(tmp_path: Path, nested: bool) -> None:
    component_dir = tmp_path / "modules" / "nf-core" / "example"
    component_dir.mkdir(parents=True)
    patch_path = component_dir / ("patches/example.diff" if nested else "example.diff")
    patch_path.parent.mkdir(parents=True, exist_ok=True)
    original = b"original user changes that must survive a declined preview\n"
    patch_path.write_bytes(original)

    install_dir = tmp_path / "staging" / "example"
    install_dir.mkdir(parents=True)
    (install_dir / "main.nf").write_text("process EXAMPLE {}\n")

    updater = SimpleNamespace(
        directory=tmp_path,
        component_type="modules",
        check_patch_paths=mock.Mock(),
    )
    with mock.patch(
        "nf_core.components.update.ComponentsDiffer.try_apply_patch",
        side_effect=LookupError("patch no longer applies"),
    ):
        applied = ComponentUpdate.try_apply_patch(
            updater,
            "example",
            "nf-core",
            patch_path.relative_to(tmp_path),
            component_dir,
            install_dir,
            write_file=False,
        )

    assert applied is False
    assert patch_path.read_bytes() == original
    assert (install_dir / patch_path.relative_to(component_dir)).read_bytes() == original
