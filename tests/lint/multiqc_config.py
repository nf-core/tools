from pathlib import Path

import yaml

import nf_core.lint


def test_multiqc_config_exists(self):
    """Test that linting fails if the multiqc_config.yml file is missing"""
    # Delete the file
    new_pipeline = self._make_pipeline_copy()
    Path(Path(new_pipeline, "assets", "multiqc_config.yml")).unlink()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.multiqc_config()
    assert result["failed"] == ["`assets/multiqc_config.yml` not found."]


def test_multiqc_config_ignore(self):
    """Test that linting succeeds if the multiqc_config.yml file is missing but ignored"""
    # Delete the file
    new_pipeline = self._make_pipeline_copy()
    Path(Path(new_pipeline, "assets", "multiqc_config.yml")).unlink()
    with open(Path(new_pipeline, ".nf-core.yml")) as f:
        content = yaml.safe_load(f)
        old_content = content.copy()
        content["lint"] = {"multiqc_config": False}
    with open(Path(new_pipeline, ".nf-core.yml"), "w") as f:
        yaml.dump(content, f)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.multiqc_config()
    assert result["ignored"] == ["`assets/multiqc_config.yml` not found, but it is ignored."]

    # cleanup
    with open(Path(new_pipeline, ".nf-core.yml"), "w") as f:
        yaml.dump(old_content, f)


def test_multiqc_config_missing_report_section_order(self):
    """Test that linting fails if the multiqc_config.yml file is missing the report_section_order"""
    new_pipeline = self._make_pipeline_copy()
    with open(Path(new_pipeline, "assets", "multiqc_config.yml")) as fh:
        mqc_yml = yaml.safe_load(fh)
    mqc_yml_tmp = mqc_yml.copy()
    mqc_yml.pop("report_section_order")
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml, fh)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.multiqc_config()
    # Reset the file
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml_tmp, fh)
    assert result["failed"] == ["`assets/multiqc_config.yml` does not contain `report_section_order`"]


def test_multiqc_incorrect_export_plots(self):
    """Test that linting fails if the multiqc_config.yml file has an incorrect value for export_plots"""
    new_pipeline = self._make_pipeline_copy()
    with open(Path(new_pipeline, "assets", "multiqc_config.yml")) as fh:
        mqc_yml = yaml.safe_load(fh)
    mqc_yml_tmp = mqc_yml.copy()
    mqc_yml["export_plots"] = False
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml, fh)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.multiqc_config()
    # Reset the file
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml_tmp, fh)
    assert result["failed"] == ["`assets/multiqc_config.yml` does not contain 'export_plots: true'."]


def test_multiqc_config_report_comment_fail(self):
    """Test that linting fails if the multiqc_config.yml file has an incorrect report_comment"""
    new_pipeline = self._make_pipeline_copy()
    with open(Path(new_pipeline, "assets", "multiqc_config.yml")) as fh:
        mqc_yml = yaml.safe_load(fh)
    mqc_yml_tmp = mqc_yml.copy()
    mqc_yml["report_comment"] = "This is a test"
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml, fh)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.multiqc_config()
    # Reset the file
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml_tmp, fh)
    assert len(result["failed"]) == 1
    assert result["failed"][0].startswith("`assets/multiqc_config.yml` does not contain a matching 'report_comment'.")


def test_multiqc_config_report_comment_release_fail(self):
    """Test that linting fails if the multiqc_config.yml file has an incorrect report_comment for a release version"""
    new_pipeline = self._make_pipeline_copy()
    with open(Path(new_pipeline, "assets", "multiqc_config.yml")) as fh:
        mqc_yml = yaml.safe_load(fh)
    mqc_yml_tmp = mqc_yml.copy()
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml, fh)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    # bump version
    lint_obj.nf_config["manifest.version"] = "1.0"
    result = lint_obj.multiqc_config()
    # Reset the file
    with open(Path(new_pipeline, "assets", "multiqc_config.yml"), "w") as fh:
        yaml.safe_dump(mqc_yml_tmp, fh)
    assert len(result["failed"]) == 1
    assert result["failed"][0].startswith("`assets/multiqc_config.yml` does not contain a matching 'report_comment'.")


def test_multiqc_config_report_comment_release_succeed(self):
    """Test that linting fails if the multiqc_config.yml file has a correct report_comment for a release version"""

    import nf_core.bump_version

    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    # bump version using the bump_version function
    nf_core.bump_version.bump_pipeline_version(lint_obj, "1.0")
    # lint again
    lint_obj._load()
    result = lint_obj.multiqc_config()
    assert "`assets/multiqc_config.yml` contains a matching 'report_comment'." in result["passed"]
