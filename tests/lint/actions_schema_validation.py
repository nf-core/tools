from pathlib import Path

import yaml

import nf_core.lint


def test_actions_schema_validation_missing_jobs(self):
    """Missing 'jobs' field should result in failure"""
    new_pipeline = self._make_pipeline_copy()

    awstest_yml_path = Path(new_pipeline) / ".github" / "workflows" / "awstest.yml"
    with open(awstest_yml_path) as fh:
        awstest_yml = yaml.safe_load(fh)
    awstest_yml.pop("jobs")
    with open(awstest_yml_path, "w") as fh:
        yaml.dump(awstest_yml, fh)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_schema_validation()

    assert "Workflow validation failed for awstest.yml: 'jobs' is a required property" in results["failed"][0]


def test_actions_schema_validation_missing_on(self):
    """Missing 'on' field should result in failure"""
    new_pipeline = self._make_pipeline_copy()

    awstest_yml_path = Path(new_pipeline) / ".github" / "workflows" / "awstest.yml"
    with open(awstest_yml_path) as fh:
        awstest_yml = yaml.safe_load(fh)
    awstest_yml.pop(True)
    with open(awstest_yml_path, "w") as fh:
        yaml.dump(awstest_yml, fh)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_schema_validation()

    assert results["failed"][0] == "Missing 'on' keyword in awstest.yml"
    assert "Workflow validation failed for awstest.yml: 'on' is a required property" in results["failed"][1]


def test_actions_schema_validation_fails_for_additional_property(self):
    """Missing 'jobs' field should result in failure"""
    new_pipeline = self._make_pipeline_copy()

    awstest_yml_path = Path(new_pipeline) / ".github" / "workflows" / "awstest.yml"
    with open(awstest_yml_path) as fh:
        awstest_yml = yaml.safe_load(fh)
    awstest_yml["not_jobs"] = awstest_yml["jobs"]
    with open(awstest_yml_path, "w") as fh:
        yaml.dump(awstest_yml, fh)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()

    results = lint_obj.actions_schema_validation()

    assert (
        "Workflow validation failed for awstest.yml: Additional properties are not allowed ('not_jobs' was unexpected)"
        in results["failed"][0]
    )
