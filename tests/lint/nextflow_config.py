import os
import re
from pathlib import Path

import nf_core.create
import nf_core.lint


def test_nextflow_config_example_pass(self):
    """Tests that config variable existence test works with good pipeline example"""
    self.lint_obj._load_pipeline_config()
    result = self.lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["warned"]) == 0


def test_nextflow_config_bad_name_fail(self):
    """Tests that config variable existence test fails with bad pipeline name"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.nf_config["manifest.name"] = "bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0


def test_nextflow_config_dev_in_release_mode_failed(self):
    """Tests that config variable existence test fails with dev version in release mode"""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()

    lint_obj.release_mode = True
    lint_obj.nf_config["manifest.version"] = "dev_is_bad_name"
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0


def test_nextflow_config_missing_test_profile_failed(self):
    """Test failure if config file does not contain `test` profile."""
    new_pipeline = self._make_pipeline_copy()
    # Change the name of the test profile so there is no such profile
    nf_conf_file = os.path.join(new_pipeline, "nextflow.config")
    with open(nf_conf_file) as f:
        content = f.read()
        fail_content = re.sub(r"\btest\b", "testfail", content)
    with open(nf_conf_file, "w") as f:
        f.write(fail_content)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) > 0
    assert len(result["warned"]) == 0


def test_default_values_match(self):
    """Test that the default values in nextflow.config match the default values defined in the nextflow_schema.json."""
    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["warned"]) == 0
    assert "Config default value correct: params.max_cpus" in str(result["passed"])
    assert "Config default value correct: params.validate_params" in str(result["passed"])


def test_default_values_fail(self):
    """Test linting fails if the default values in nextflow.config do not match the ones defined in the nextflow_schema.json."""
    new_pipeline = self._make_pipeline_copy()
    # Change the default value of max_cpus in nextflow.config
    nf_conf_file = Path(new_pipeline) / "nextflow.config"
    with open(nf_conf_file) as f:
        content = f.read()
        fail_content = re.sub(r"\bmax_cpus\s*=\s*16\b", "max_cpus = 0", content)
    with open(nf_conf_file, "w") as f:
        f.write(fail_content)
    # Change the default value of max_memory in nextflow_schema.json
    nf_schema_file = Path(new_pipeline) / "nextflow_schema.json"
    with open(nf_schema_file) as f:
        content = f.read()
        fail_content = re.sub(r'"default": "128.GB"', '"default": "18.GB"', content)
    with open(nf_schema_file, "w") as f:
        f.write(fail_content)
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 2
    assert (
        "Config default value incorrect: `params.max_cpus` is set as `16` in `nextflow_schema.json` but is `0` in `nextflow.config`."
        in result["failed"]
    )
    assert (
        "Config default value incorrect: `params.max_memory` is set as `18.GB` in `nextflow_schema.json` but is `128.GB` in `nextflow.config`."
        in result["failed"]
    )


def test_catch_params_assignment_in_main_nf(self):
    """Test linting fails if main.nf contains an assignment to a parameter from nextflow_schema.json."""
    new_pipeline = self._make_pipeline_copy()
    # Add parameter assignment in main.nf
    main_nf_file = Path(new_pipeline) / "main.nf"
    with open(main_nf_file, "a") as f:
        f.write("params.max_time = 42")
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 1
    assert (
        result["failed"][0]
        == "Config default value incorrect: `params.max_time` is set as `240.h` in `nextflow_schema.json` but is `null` in `nextflow.config`."
    )


def test_allow_params_reference_in_main_nf(self):
    """Test linting allows for references like `params.aligner == 'bwa'` in main.nf. The test will detect if the bug mentioned in GitHub-issue #2833 reemerges."""
    new_pipeline = self._make_pipeline_copy()
    # Add parameter reference in main.nf
    main_nf_file = Path(new_pipeline) / "main.nf"
    with open(main_nf_file, "a") as f:
        f.write("params.max_time == 42")
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 0


def test_default_values_ignored(self):
    """Test ignoring linting of default values."""
    new_pipeline = self._make_pipeline_copy()
    # Add max_cpus to the ignore list
    nf_core_yml = Path(new_pipeline) / ".nf-core.yml"
    with open(nf_core_yml, "w") as f:
        f.write(
            "repository_type: pipeline\nlint:\n  nextflow_config:\n    - config_defaults:\n      - params.max_cpus\n"
        )
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    lint_obj._load_lint_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["ignored"]) == 1
    assert "Config default value correct: params.max_cpu" not in str(result["passed"])
    assert "Config default ignored: params.max_cpus" in str(result["ignored"])


def test_default_values_float(self):
    """Test comparing two float values."""
    new_pipeline = self._make_pipeline_copy()
    # Add a float value `dummy=0.0001` to the nextflow.config below `validate_params`
    nf_conf_file = Path(new_pipeline) / "nextflow.config"
    with open(nf_conf_file) as f:
        content = f.read()
        fail_content = re.sub(
            r"validate_params\s*=\s*true", "params.validate_params = true\ndummy = 0.000000001", content
        )
    with open(nf_conf_file, "w") as f:
        f.write(fail_content)
    # Add a float value `dummy` to the nextflow_schema.json
    nf_schema_file = Path(new_pipeline) / "nextflow_schema.json"
    with open(nf_schema_file) as f:
        content = f.read()
        fail_content = re.sub(
            r'"validate_params": {',
            '    "dummy": {"type": "number","default":0.000000001},\n"validate_params": {',
            content,
        )
    with open(nf_schema_file, "w") as f:
        f.write(fail_content)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()
    assert len(result["failed"]) == 0
    assert len(result["warned"]) == 0
    assert "Config default value correct: params.dummy" in str(result["passed"])


def test_default_values_float_fail(self):
    """Test comparing two float values."""
    new_pipeline = self._make_pipeline_copy()
    # Add a float value `dummy=0.0001` to the nextflow.config below `validate_params`
    nf_conf_file = Path(new_pipeline) / "nextflow.config"
    with open(nf_conf_file) as f:
        content = f.read()
        fail_content = re.sub(
            r"validate_params\s*=\s*true", "params.validate_params = true\ndummy = 0.000000001", content
        )
    with open(nf_conf_file, "w") as f:
        f.write(fail_content)
    # Add a float value `dummy` to the nextflow_schema.json
    nf_schema_file = Path(new_pipeline) / "nextflow_schema.json"
    with open(nf_schema_file) as f:
        content = f.read()
        fail_content = re.sub(
            r'"validate_params": {', '    "dummy": {"type": "float","default":0.000001},\n"validate_params": {', content
        )
    with open(nf_schema_file, "w") as f:
        f.write(fail_content)

    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load_pipeline_config()
    result = lint_obj.nextflow_config()

    assert len(result["failed"]) == 1
    assert len(result["warned"]) == 0
    assert "Config default value incorrect: `params.dummy" in str(result["failed"])
