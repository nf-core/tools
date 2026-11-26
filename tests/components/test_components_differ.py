from pathlib import Path

import pytest

from nf_core.components.components_differ import ComponentsDiffer

COMPONENT = "fastqc"
FILE = "main.nf.test.snap"


@pytest.mark.parametrize(
    "old_text, new_text",
    [
        # a change in the last three lines of a file without a final newline (#4641)
        ('{\n    "a": 1,\n    "timestamp": "old"\n    }\n}', '{\n    "a": 1,\n    "timestamp": "new"\n    }\n}'),
        # the last line itself changes
        ("a\nb", "a\nc"),
        # the final newline is added
        ("a\nb", "a\nb\n"),
    ],
)
def test_patch_applies_to_file_without_final_newline(tmp_path, old_text, new_text):
    old_dir = tmp_path / "old" / COMPONENT
    new_dir = tmp_path / "new" / COMPONENT
    for directory, text in ((old_dir, old_text), (new_dir, new_text)):
        directory.mkdir(parents=True)
        (directory / FILE).write_text(text)

    patch_path = tmp_path / "fastqc.diff"
    component_relpath = Path("modules", "nf-core", COMPONENT)
    ComponentsDiffer.write_diff_file(
        patch_path,
        COMPONENT,
        "nf-core",
        old_dir,
        new_dir,
        for_git=False,
        dsp_from_dir=component_relpath,
        dsp_to_dir=component_relpath,
    )
    assert "\\ No newline at end of file\n" in patch_path.read_text()

    patched = ComponentsDiffer.try_apply_patch("modules", COMPONENT, "nf-core", patch_path, old_dir)
    assert patched[FILE] == new_text.splitlines(keepends=True)
    reverted = ComponentsDiffer.try_apply_patch("modules", COMPONENT, "nf-core", patch_path, new_dir, reverse=True)
    assert reverted[FILE] == old_text.splitlines(keepends=True)


def test_per_file_patch_keeps_removed_yaml_separator(tmp_path):
    """A removed YAML separator ("----") should be kept as a patch line, not mistaken for a new file header."""
    patch_file_sample = (
        "--- modules/nf-core/samtools/dict/environment.yml\n"
        "+++ modules/nf-core/samtools/dict/environment.yml\n"
        "@@ -1,2 +1,2 @@\n"
        "----\n"
        "+name: samtools_dict\n"
        " channels:\n"
    )
    path_patch = tmp_path / "path_patch.diff"
    path_patch.write_text(patch_file_sample)
    result = ComponentsDiffer.per_file_patch(path_patch)
    assert list(result) == ["modules/nf-core/samtools/dict/environment.yml"]
    assert "----\n" in result["modules/nf-core/samtools/dict/environment.yml"]
