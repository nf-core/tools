from nf_core.components.components_differ import ComponentsDiffer


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
