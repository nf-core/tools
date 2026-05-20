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


def check_config(cfg: dict, fail: bool, ctx: dict = {}) -> None:
    assert isinstance(cfg, dict)
    assert isinstance(fail, bool)
    assert isinstance(ctx, dict)

    with init_context(ctx):
        if fail:
            failed = False
            try:
                ConfigsCreateConfig(**cfg)
            except ValidationError:
                failed = True
            assert failed
        else:
            ConfigsCreateConfig(**cfg)


def test_pipe_name():
    cfg_valid = {"config_pipeline_name": "Some pipeline name."}
    cfg_invalid = {"config_pipeline_name": ""}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)


def test_pipe_path():
    cfg_valid = {"config_pipeline_path": "."}
    cfg_invalid_1 = {"config_pipeline_path": ""}
    cfg_invalid_2 = {"config_pipeline_path": "./_this_path_doesnt_exist_"}

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid_1, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid_2, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_invalid_1, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_invalid_2, fail=False, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid_1, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid_2, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_invalid_1, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_invalid_2, fail=False, ctx=Context.NF_INFRA_LOCAL.value)


def test_config_name():
    cfg_valid_custom = {"general_config_name": "A valid custom config Name"}
    cfg_valid_nfcore = {"general_config_name": "a valid nfcore config name"}
    cfg_invalid = {"general_config_name": ""}

    # Test custom infra config context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_valid_custom, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nfcore infra config context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_valid_custom, fail=True, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=True, ctx=Context.NF_INFRA_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_valid_custom, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_valid_custom, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)


def test_contact_name():
    cfg_valid = {"config_profile_contact": "some name"}
    cfg_invalid = {"config_profile_contact": ""}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_INFRA_LOCAL.value)


def test_handle():
    cfg_valid = {"config_profile_handle": "@someHandle"}
    cfg_invalid = {"config_profile_handle": "BadHandle"}
    cfg_empty = {"config_profile_handle": ""}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_empty, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=True, ctx=Context.NF_INFRA_LOCAL.value)


def test_description():
    cfg_valid = {"config_profile_description": "A good description"}
    cfg_invalid = {"config_profile_description": ""}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_INFRA_LOCAL.value)


def test_url():
    cfg_valid = {"config_profile_url": "http://some.url"}
    cfg_invalid = {"config_profile_url": "a.bad.url"}
    cfg_empty = {"config_profile_url": ""}

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=True, ctx=Context.NF_INFRA_LOCAL.value)

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_empty, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)


def test_proc_cpu_mem():
    for field in [
        "default_process_ncpus",
        "default_process_memgb",
        "custom_process_ncpus",
        "custom_process_memgb",
    ]:
        cfg_valid = {field: "2"}
        cfg_invalid_str = {field: "hello"}
        cfg_invalid_float = {field: "1.2"}
        cfg_invalid_zero = {field: "0"}
        cfg_invalid_neg = {field: "-2"}
        cfg_empty = {field: ""}

        # Test nf-core pipeline context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        # Should fail
        check_config(cfg_invalid_str, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_invalid_float, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_invalid_zero, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_invalid_neg, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

        # Test custom pipeline context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        # Should fail
        check_config(cfg_invalid_str, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_invalid_float, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_invalid_zero, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_invalid_neg, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

        # Test custom infra context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_str, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_float, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_zero, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_neg, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

        # Test nf-core infra context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_str, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_float, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_zero, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_neg, fail=False, ctx=Context.NF_INFRA_LOCAL.value)


def test_proc_hours():
    for field in [
        "default_process_hours",
        "custom_process_hours",
    ]:
        cfg_valid = {field: "2"}
        cfg_valid_float = {field: "1.2"}
        cfg_valid_zero = {field: "0"}
        cfg_invalid_str = {field: "hello"}
        cfg_invalid_neg = {field: "-2"}
        cfg_empty = {field: ""}

        # Test nf-core pipeline context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_valid_float, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_valid_zero, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
        # Should fail
        check_config(cfg_invalid_str, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
        check_config(cfg_invalid_neg, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

        # Test custom pipeline context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_valid_float, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_valid_zero, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        # Should fail
        check_config(cfg_invalid_str, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)
        check_config(cfg_invalid_neg, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

        # Test custom infra context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_valid_float, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_valid_zero, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_str, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
        check_config(cfg_invalid_neg, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)

        # Test nf-core infra context
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_valid_float, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_valid_zero, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_empty, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_str, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
        check_config(cfg_invalid_neg, fail=False, ctx=Context.NF_INFRA_LOCAL.value)


def test_proc_name():
    cfg_valid_nfcore = {"custom_process_name_id": "SOME.PROC_ESS:NAME*"}
    cfg_valid_custom = {"custom_process_name_id": "a_process_name"}
    cfg_empty = {"custom_process_name_id": ""}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_valid_custom, fail=True, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_empty, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_valid_custom, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_empty, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_valid_custom, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.NF_INFRA_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid_nfcore, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_valid_custom, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)


def test_proc_label():
    cfg_valid_nfcore = {"custom_process_label_id": "some_label"}
    cfg_valid_custom = {"custom_process_label_id": "ANOTHER_LABEL"}
    cfg_empty = {"custom_process_label_id": ""}


def test_proc_queue():
    cfg_valid = {}


def test_save_loc():
    cfg_valid = {}


def test_scheduler():
    cfg_valid = {}


def test_default_queue():
    cfg_valid = {}


def test_modules():
    cfg_valid = {}


def test_container():
    cfg_valid = {}


def test_cpu_mem():
    cfg_valid = {}


def test_hours():
    cfg_valid = {}


def test_cachedir():
    cfg_valid = {}


def test_igenomes():
    cfg_valid = {}


def test_scratch():
    cfg_valid = {}


def test_retires():
    cfg_valid = {}


def test_queue_stat_int():
    cfg_valid = {}


def test_queue_size():
    cfg_valid = {}


def test_poll_int():
    cfg_valid = {}


def test_submit_rate():
    cfg_valid = {}
