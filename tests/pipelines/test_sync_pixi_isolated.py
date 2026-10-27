"""Exercise sync dirtiness against real Git indexes without Nextflow setup."""

from types import SimpleNamespace

import git
import pytest

from nf_core.pipelines.sync import PipelineSync


@pytest.mark.parametrize(
    ("mode", "dirty"),
    [
        ("clean", False),
        ("untracked_pixi", False),
        ("untracked_source", True),
        ("edited_source", True),
        ("edited_tracked_pixi", True),
        ("staged_pixi", True),
    ],
)
def test_sync_dirtiness_does_not_hide_tracked_changes(tmp_path, mode, dirty):
    repo = git.Repo.init(tmp_path)
    source = tmp_path / "main.nf"
    source.write_text("original\n")
    tracked_pixi = tmp_path / ".pixi" / "locked.txt"
    tracked_pixi.parent.mkdir()
    tracked_pixi.write_text("original\n")
    repo.index.add(["main.nf", ".pixi/locked.txt"])
    repo.index.commit("baseline")

    if mode == "untracked_pixi":
        (tmp_path / ".pixi" / "local.txt").write_text("untracked\n")
    elif mode == "untracked_source":
        (tmp_path / "notes.txt").write_text("untracked\n")
    elif mode == "edited_source":
        source.write_text("edited\n")
    elif mode == "edited_tracked_pixi":
        tracked_pixi.write_text("edited\n")
    elif mode == "staged_pixi":
        tracked_pixi.write_text("staged\n")
        repo.index.add([".pixi/locked.txt"])

    assert PipelineSync._has_sync_changes(SimpleNamespace(repo=repo)) is dirty
