from pathlib import Path

import nf_core.create
import nf_core.lint


def test_withname_in_modules_config(self):
    """Tests finding withName in modules.config passes linting."""

    new_pipeline = self._make_pipeline_copy()
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.modules_config()
    assert len(result["failed"]) == 0
    assert any(["contain `FASTQC`" in passed for passed in result["passed"]])


def test_superfluous_withname_in_modules_config_fails(self):
    """Tests finding withName in modules.config fails linting."""
    new_pipeline = self._make_pipeline_copy()
    # Add withName to modules.config
    modules_config = Path(new_pipeline) / "conf" / "modules.config"
    with open(modules_config, "a") as f:
        f.write("withName:CUSTOM_DUMPSOFTWAREVERSIONS {\n cache = false \n}")
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.modules_config()
    assert len(result["failed"]) == 1
    assert result["failed"][0].startswith("`conf/modules.config` contains `withName:CUSTOM_DUMPSOFTWAREVERSIONS`")


def test_superfluous_withname_in_base_config_fails(self):
    """Tests finding withName in base.config fails linting."""
    new_pipeline = self._make_pipeline_copy()
    # Add withName to base.config
    base_config = Path(new_pipeline) / "conf" / "base.config"
    with open(base_config, "a") as f:
        f.write("withName:CUSTOM_DUMPSOFTWAREVERSIONS {\n cache = false \n}")
    lint_obj = nf_core.lint.PipelineLint(new_pipeline)
    lint_obj._load()
    result = lint_obj.base_config()
    assert len(result["failed"]) == 1
    assert result["failed"][0].startswith("`conf/base.config` contains `withName:CUSTOM_DUMPSOFTWAREVERSIONS`")
