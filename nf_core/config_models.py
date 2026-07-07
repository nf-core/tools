"""Pydantic models for the `.nf-core.yml` configuration file.

Kept separate from nf_core.utils so that pydantic is only imported
when the config file is actually parsed.
"""

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NFCoreTemplateConfig(BaseModel):
    """Template configuration schema"""

    org: str | None = None
    """ Organisation name """
    name: str | None = None
    """ Pipeline name """
    description: str | None = None
    """ Pipeline description """
    author: str | None = None
    """ Pipeline author """
    version: str | None = None
    """ Pipeline version """
    force: bool | None = True
    """ Force overwrite of existing files """
    outdir: str | Path | None = None
    """ Output directory """
    skip_features: list | None = None
    """ Skip features. See https://nf-co.re/docs/nf-core-tools/pipelines/create for a list of features. """
    is_nfcore: bool | None = None
    """ Whether the pipeline is an nf-core pipeline. """

    # convert outdir to str
    @field_validator("outdir")
    @classmethod
    def outdir_to_str(cls, v: str | Path | None) -> str | None:
        if v is not None:
            v = str(v)
        return v

    def __getitem__(self, item: str) -> Any:
        if self is None:
            return None
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class NFCoreYamlLintConfig(BaseModel):
    """
    schema for linting config in `.nf-core.yml` should cover:

    .. code-block:: yaml

        files_unchanged:
            - .github/workflows/branch.yml
        modules_config: False
        modules_config:
                - fastqc
        # merge_markers: False
        merge_markers:
                - docs/my_pdf.pdf
        nextflow_config: False
        nextflow_config:
            - manifest.name
            - config_defaults:
                - params.annotation_db
                - params.multiqc_comment_headers
                - params.custom_table_headers
        # multiqc_config: False
        multiqc_config:
            - report_section_order
            - report_comment
        files_exist:
            - CITATIONS.md
        template_strings: False
        template_strings:
                - docs/my_pdf.pdf
        nfcore_components: False
        # nf_test_content: False
        nf_test_content:
            - tests/<test_name>.nf.test
            - tests/nextflow.config
            - nf-test.config
    """

    files_unchanged: bool | list[str] | None = None
    """ List of files that should not be changed """
    modules_config: bool | list[str] | None = None
    """ List of modules that should not be changed """
    merge_markers: bool | list[str] | None = None
    """ List of files that should not contain merge markers """
    nextflow_config: bool | list[str | dict[str, list[str]]] | None = None
    """ List of Nextflow config files that should not be changed """
    nf_test_content: bool | list[str] | None = None
    """ List of nf-test content that should not be changed """
    multiqc_config: bool | list[str] | None = None
    """ List of MultiQC config options that be changed """
    files_exist: bool | list[str] | None = None
    """ List of files that can not exist """
    template_strings: bool | list[str] | None = None
    """ List of files that can contain template strings """
    readme: bool | list[str] | None = None
    """ Lint the README.md file """
    nfcore_components: bool | None = None
    """ Lint all required files to use nf-core modules and subworkflows """
    actions_nf_test: bool | None = None
    """ Lint all required files to use GitHub Actions CI """
    actions_awstest: bool | None = None
    """ Lint all required files to run tests on AWS """
    actions_awsfulltest: bool | None = None
    """ Lint all required files to run full tests on AWS """
    pipeline_todos: bool | None = None
    """ Lint for TODOs statements"""
    pipeline_if_empty_null: bool | None = None
    """ Lint for ifEmpty(null) statements"""
    plugin_includes: bool | None = None
    """ Lint for nextflow plugin """
    pipeline_name_conventions: bool | None = None
    """ Lint for pipeline name conventions """
    schema_lint: bool | None = None
    """ Lint nextflow_schema.json file"""
    schema_params: bool | None = None
    """ Lint schema for all params """
    system_exit: bool | None = None
    """ Lint for System.exit calls in groovy/nextflow code """
    schema_description: bool | None = None
    """ Check that every parameter in the schema has a description. """
    actions_schema_validation: bool | None = None
    """ Lint GitHub Action workflow files with schema"""
    modules_json: bool | None = None
    """ Lint modules.json file """
    modules_structure: bool | None = None
    """ Lint modules structure """
    base_config: bool | None = None
    """ Lint base.config file """
    nfcore_yml: bool | None = None
    """ Lint nf-core.yml """
    version_consistency: bool | None = None
    """ Lint for version consistency """
    included_configs: bool | None = None
    """ Lint for included configs """
    local_component_structure: bool | None = None
    """ Lint local components use correct structure mirroring remote"""
    container_configs: bool | None = None
    """ Lint that container configuration files in conf/ are up to date """
    rocrate_readme_sync: bool | None = None
    """ Lint for README.md and rocrate.json sync """

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        if getattr(self, item, default) is None:
            return default
        return getattr(self, item, default)

    def __setitem__(self, item: str, value: Any) -> None:
        setattr(self, item, value)


class NFCoreYamlConfig(BaseModel):
    """.nf-core.yml configuration file schema"""

    model_config = ConfigDict(populate_by_name=True)

    repository_type: Literal["pipeline", "modules"] | None = None
    """ Type of repository """
    nf_core_version: str | None = None
    """ Version of nf-core/tools used to create/update the pipeline """
    org_path: str | None = None
    """ Path to the organisation's modules repository (used for modules repo_type only) """
    lint: NFCoreYamlLintConfig | None = None
    """ Pipeline linting configuration, see https://nf-co.re/docs/nf-core-tools/pipelines/lint#linting-config for examples and documentation """
    template: NFCoreTemplateConfig | None = None
    """ Pipeline template configuration """
    bump_version: dict[str, bool] | None = None
    """ Disable bumping of the version for a module/subworkflow (when repository_type is modules). See https://nf-co.re/docs/nf-core-tools/modules/bump-versions for more information. """
    update: dict[str, str | bool | dict[str, str | dict[str, str | bool]]] | None = None
    """ Disable updating specific modules/subworkflows (when repository_type is pipeline). See https://nf-co.re/docs/nf-core-tools/modules/update for more information. """
    container_registry: list[str] | None = Field(default=None, alias="container-registry")
    """ Additional container registry prefixes allowed when linting container directives. """

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __setitem__(self, item: str, value: Any) -> None:
        setattr(self, item, value)

    def model_dump(self, **kwargs) -> dict[str, Any]:
        # Get the initial data
        config = super().model_dump(**kwargs)

        if self.repository_type == "modules":
            # Fields to exclude for modules
            fields_to_exclude = ["template", "update"]
        else:  # pipeline
            # Fields to exclude for pipeline
            fields_to_exclude = ["bump_version", "org_path"]

        # Remove the fields based on repository_type
        for field in fields_to_exclude:
            config.pop(field, None)

        return config
