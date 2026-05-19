from nf_core.configs.create.utils import ConfigsCreateConfig, init_context

from pydantic_core._pydantic_core import ValidationError

from enum import Enum


class Context(Enum):

    NF_INFRA_HPC = {
        "is_nfcore": True,
        "is_infrastructure": True,
        "is_hpc": True,
    }
    NF_INFRA_LOCAL = {
        "is_nfcore": True,
        "is_infrastructure": True,
        "is_hpc": False,
    }
    NF_PIPE_HPC = {
        "is_nfcore": True,
        "is_infrastructure": False,
        "is_hpc": True,
    }
    NF_PIPE_LOCAL = {
        "is_nfcore": True,
        "is_infrastructure": False,
        "is_hpc": False,
    }
    CUSTOM_INFRA_HPC = {
        "is_nfcore": False,
        "is_infrastructure": True,
        "is_hpc": True,
    }
    CUSTOM_INFRA_LOCAL = {
        "is_nfcore": False,
        "is_infrastructure": True,
        "is_hpc": False,
    }
    CUSTOM_PIPE_HPC = {
        "is_nfcore": False,
        "is_infrastructure": False,
        "is_hpc": True,
    }
    CUSTOM_PIPE_LOCAL = {
        "is_nfcore": False,
        "is_infrastructure": False,
        "is_hpc": False,
    }


def test_pipe_name():
    cfg_valid = {"config_pipeline_name": "Some pipeline name."}
    cfg_invalid = {"config_pipeline_name": ""}

    # Test nf-core pipeline context
    with init_context(Context.NF_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid)
        except ValidationError:
            failed = True
        assert failed

    # Test custom pipeline context
    with init_context(Context.CUSTOM_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid)

    # Test custom infra context
    with init_context(Context.CUSTOM_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid)

    # Test nf-core infra context
    with init_context(Context.NF_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid)


def test_pipe_path():
    cfg_valid = {"config_pipeline_path": "."}
    cfg_invalid_1 = {"config_pipeline_path": ""}
    cfg_invalid_2 = {"config_pipeline_path": "./_this_path_doesnt_exist_"}

    # Test custom pipeline context
    with init_context(Context.CUSTOM_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid_1)
        except ValidationError:
            failed = True
        assert failed

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid_2)
        except ValidationError:
            failed = True
        assert failed

    # Test nf-core pipeline context
    with init_context(Context.NF_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid_1)
        ConfigsCreateConfig(**cfg_invalid_2)

    # Test custom infra context
    with init_context(Context.CUSTOM_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid_1)
        ConfigsCreateConfig(**cfg_invalid_2)

    # Test nf-core infra context
    with init_context(Context.NF_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid)
        ConfigsCreateConfig(**cfg_invalid_1)
        ConfigsCreateConfig(**cfg_invalid_2)


def test_config_name():
    cfg_valid_custom = {"general_config_name": "A valid custom config Name"}
    cfg_valid_nfcore = {"general_config_name": "a valid nfcore config name"}
    cfg_invalid = {"general_config_name": ""}

    # Test custom config context
    with init_context(Context.CUSTOM_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid_nfcore)
        ConfigsCreateConfig(**cfg_valid_custom)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid)
        except ValidationError:
            failed = True
        assert failed

    # Test nfcore config context
    with init_context(Context.NF_INFRA_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid_nfcore)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_valid_custom)
        except ValidationError:
            failed = True
        assert failed

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid)
        except ValidationError:
            failed = True
        assert failed

    # Test custom pipeline context
    with init_context(Context.CUSTOM_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid_nfcore)
        ConfigsCreateConfig(**cfg_valid_custom)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid)
        except ValidationError:
            failed = True
        assert failed

    # Test nf-core pipeline context
    with init_context(Context.NF_PIPE_LOCAL.value):
        # Should succeed
        ConfigsCreateConfig(**cfg_valid_nfcore)

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_valid_custom)
        except ValidationError:
            failed = True
        assert failed

        # Should fail
        failed = False
        try:
            ConfigsCreateConfig(**cfg_invalid)
        except ValidationError:
            failed = True
        assert failed
