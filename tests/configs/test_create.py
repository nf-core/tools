from nf_core.configs.create.utils import ConfigsCreateConfig, init_context, SUPPORTED_SCHEDULERS, SUPPORTED_CONTAINERS

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
    cfg_valid = {"custom_process_queue": "somequeue"}
    cfg_valid_empty = {"custom_process_queue": ""}
    cfg_invalid_spaces = {"custom_process_queue": "a bad queue"}

    # Test nf-core pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    check_config(cfg_valid_empty, fail=False, ctx=Context.NF_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid_spaces, fail=True, ctx=Context.NF_PIPE_LOCAL.value)

    # Test custom pipeline context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    check_config(cfg_valid_empty, fail=False, ctx=Context.CUSTOM_PIPE_LOCAL.value)
    # Should fail
    check_config(cfg_invalid_spaces, fail=True, ctx=Context.CUSTOM_PIPE_LOCAL.value)

    # Test nf-core infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_valid_empty, fail=False, ctx=Context.NF_INFRA_LOCAL.value)
    check_config(cfg_invalid_spaces, fail=False, ctx=Context.NF_INFRA_LOCAL.value)

    # Test custom infra context
    # Should succeed
    check_config(cfg_valid, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_valid_empty, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)
    check_config(cfg_invalid_spaces, fail=False, ctx=Context.CUSTOM_INFRA_LOCAL.value)


def test_save_loc():
    cfg_valid = {"savelocation": "."}
    cfg_invalid_empty = {"savelocation": ""}
    cfg_invalid_missing = {"savelocation": "./_this_path_doesnt_exist_"}

    # Test all contexts
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.NF_INFRA_LOCAL.value,
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        # Should fail
        check_config(cfg_invalid_empty, fail=True, ctx=ctx)
        check_config(cfg_invalid_missing, fail=True, ctx=ctx)


def test_scheduler():
    cfg_empty = {"scheduler": ""}
    cfg_unsupported = {"scheduler": "nonexistant_scheduler"}

    # Test all contexts other than INFRA_HPC
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.NF_INFRA_LOCAL.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
    ]:
        # Should succeed
        check_config(cfg_empty, fail=False, ctx=ctx)
        check_config(cfg_unsupported, fail=False, ctx=ctx)

    # Test INFRA_HPC contexts
    for ctx in [
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        for sch in SUPPORTED_SCHEDULERS:
            cfg_valid = {"scheduler": sch}
            check_config(cfg_valid, fail=False, ctx=ctx)
        # Should fail
        check_config(cfg_empty, fail=True, ctx=ctx)
        check_config(cfg_unsupported, fail=True, ctx=ctx)


def test_container():
    valid_cfgs = [
        {"container_system": ct}
        for ct in SUPPORTED_CONTAINERS
    ]
    invalid_cfg = {"container_system": "imaginary_container_system"}
    empty_cfg = {"container_system": ""}

    # Test all contexts
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.NF_INFRA_LOCAL.value,
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        for cfg_valid in valid_cfgs:
            check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(empty_cfg, fail=False, ctx=ctx)
        # Shoudl fail
        check_config(invalid_cfg, fail=True, ctx=ctx)


def test_cpu_mem_retries():
    for field in [
        "cpus",
        "memory",
        "retries",
    ]:
        cfg_valid = {field: "2"}
        cfg_invalid_str = {field: "hello"}
        cfg_invalid_float = {field: "1.2"}
        cfg_invalid_zero = {field: "0"}
        cfg_invalid_neg = {field: "-2"}
        cfg_empty = {field: ""}

        # Test all INFRA contexts
        for ctx in [
            Context.NF_INFRA_LOCAL.value,
            Context.NF_INFRA_HPC.value,
            Context.CUSTOM_INFRA_LOCAL.value,
            Context.CUSTOM_INFRA_HPC.value,
        ]:
            # Should succeed
            check_config(cfg_valid, fail=False, ctx=ctx)
            # Shoudl fail
            check_config(cfg_invalid_str, fail=True, ctx=ctx)
            check_config(cfg_invalid_float, fail=True, ctx=ctx)
            check_config(cfg_invalid_zero, fail=True, ctx=ctx)
            check_config(cfg_invalid_neg, fail=True, ctx=ctx)
            check_config(cfg_empty, fail=True, ctx=ctx)

        # Test all PIPE contexts
        for ctx in [
            Context.NF_PIPE_LOCAL.value,
            Context.NF_PIPE_HPC.value,
            Context.CUSTOM_PIPE_LOCAL.value,
            Context.CUSTOM_PIPE_HPC.value,
        ]:
            # Should succeed
            check_config(cfg_valid, fail=False, ctx=ctx)
            check_config(cfg_invalid_str, fail=False, ctx=ctx)
            check_config(cfg_invalid_float, fail=False, ctx=ctx)
            check_config(cfg_invalid_zero, fail=False, ctx=ctx)
            check_config(cfg_invalid_neg, fail=False, ctx=ctx)
            check_config(cfg_empty, fail=False, ctx=ctx)


def test_hours():
    cfg_valid = {"time": "2"}
    cfg_valid_float = {"time": "1.2"}
    cfg_valid_zero = {"time": "0"}
    cfg_invalid_str = {"time": "hello"}
    cfg_invalid_neg = {"time": "-2"}
    cfg_empty = {"time": ""}

    # Test all INFRA contexts
    for ctx in [
        Context.NF_INFRA_LOCAL.value,
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_valid_zero, fail=False, ctx=ctx)
        # Shoudl fail
        check_config(cfg_invalid_str, fail=True, ctx=ctx)
        check_config(cfg_invalid_neg, fail=True, ctx=ctx)
        check_config(cfg_empty, fail=True, ctx=ctx)

    # Test all PIPE contexts
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_valid_zero, fail=False, ctx=ctx)
        check_config(cfg_invalid_str, fail=False, ctx=ctx)
        check_config(cfg_invalid_neg, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)


def test_cache_scratch_dirs():
    for field in [
        "cachedir",
        "scratch_dir",
    ]:
        cfg_valid_abs = {field: "/an/absolute/path"}
        cfg_valid_home = {field: "~/a/path/in/home"}
        cfg_valid_env = {field: "${SOME}/env/prefixed/path"}
        cfg_empty = {field: ""}
        cfg_invalid_rel = {field: "a/relative/path"}

        # Test all contexts
        for ctx in [
            Context.NF_PIPE_LOCAL.value,
            Context.NF_PIPE_HPC.value,
            Context.NF_INFRA_LOCAL.value,
            Context.NF_INFRA_HPC.value,
            Context.CUSTOM_PIPE_LOCAL.value,
            Context.CUSTOM_PIPE_HPC.value,
            Context.CUSTOM_INFRA_LOCAL.value,
            Context.CUSTOM_INFRA_HPC.value,
        ]:
            # Should succeed
            check_config(cfg_valid_abs, fail=False, ctx=ctx)
            check_config(cfg_valid_home, fail=False, ctx=ctx)
            check_config(cfg_valid_env, fail=False, ctx=ctx)
            check_config(cfg_empty, fail=False, ctx=ctx)
            # Should fail
            check_config(cfg_invalid_rel, fail=True, ctx=ctx)


def test_igenomes():
    cfg_valid_abs = {"igenomes_cachedir": "/an/absolute/path"}
    cfg_valid_home = {"igenomes_cachedir": "~/a/path/in/home"}
    cfg_valid_env = {"igenomes_cachedir": "${SOME}/env/prefixed/path"}
    cfg_valid_s3 = {"igenomes_cachedir": "s3://some/s3/bucket"}
    cfg_empty = {"igenomes_cachedir": ""}
    cfg_invalid_rel = {"igenomes_cachedir": "a/relative/path"}

    # Test all contexts
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.NF_INFRA_LOCAL.value,
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid_abs, fail=False, ctx=ctx)
        check_config(cfg_valid_home, fail=False, ctx=ctx)
        check_config(cfg_valid_env, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)
        check_config(cfg_valid_s3, fail=False, ctx=ctx)
        # Should fail
        check_config(cfg_invalid_rel, fail=True, ctx=ctx)


def test_queue_stat_int():
    cfg_valid = {"queue_stat_interval": "2"}
    cfg_valid_float = {"queue_stat_interval": "1.2"}
    cfg_invalid_zero = {"queue_stat_interval": "0"}
    cfg_invalid_str = {"queue_stat_interval": "hello"}
    cfg_invalid_neg = {"queue_stat_interval": "-2"}
    cfg_empty = {"queue_stat_interval": ""}

    # Test all INFRA_HPC contexts
    for ctx in [
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)
        # Shoudl fail
        check_config(cfg_invalid_zero, fail=True, ctx=ctx)
        check_config(cfg_invalid_str, fail=True, ctx=ctx)
        check_config(cfg_invalid_neg, fail=True, ctx=ctx)

    # Test all PIPE and INFRA_LOCAL contexts
    for ctx in [
        Context.NF_INFRA_LOCAL.value,
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_invalid_zero, fail=False, ctx=ctx)
        check_config(cfg_invalid_str, fail=False, ctx=ctx)
        check_config(cfg_invalid_neg, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)


def test_queue_size_submit_rate():
    for field in [
        "queue_size",
        "submit_rate",
    ]:
        cfg_valid = {field: "2"}
        cfg_invalid_str = {field: "hello"}
        cfg_invalid_float = {field: "1.2"}
        cfg_invalid_zero = {field: "0"}
        cfg_invalid_neg = {field: "-2"}
        cfg_empty = {field: ""}

        # Test all INFRA contexts
        for ctx in [
            Context.NF_INFRA_LOCAL.value,
            Context.NF_INFRA_HPC.value,
            Context.CUSTOM_INFRA_LOCAL.value,
            Context.CUSTOM_INFRA_HPC.value,
        ]:
            # Should succeed
            check_config(cfg_valid, fail=False, ctx=ctx)
            check_config(cfg_empty, fail=False, ctx=ctx)
            # Shoudl fail
            check_config(cfg_invalid_str, fail=True, ctx=ctx)
            check_config(cfg_invalid_float, fail=True, ctx=ctx)
            check_config(cfg_invalid_zero, fail=True, ctx=ctx)
            check_config(cfg_invalid_neg, fail=True, ctx=ctx)

        # Test all PIPE contexts
        for ctx in [
            Context.NF_PIPE_LOCAL.value,
            Context.NF_PIPE_HPC.value,
            Context.CUSTOM_PIPE_LOCAL.value,
            Context.CUSTOM_PIPE_HPC.value,
        ]:
            # Should succeed
            check_config(cfg_valid, fail=False, ctx=ctx)
            check_config(cfg_invalid_str, fail=False, ctx=ctx)
            check_config(cfg_invalid_float, fail=False, ctx=ctx)
            check_config(cfg_invalid_zero, fail=False, ctx=ctx)
            check_config(cfg_invalid_neg, fail=False, ctx=ctx)
            check_config(cfg_empty, fail=False, ctx=ctx)


def test_poll_int():
    cfg_valid = {"poll_interval": "2"}
    cfg_valid_float = {"poll_interval": "1.2"}
    cfg_invalid_zero = {"poll_interval": "0"}
    cfg_invalid_str = {"poll_interval": "hello"}
    cfg_invalid_neg = {"poll_interval": "-2"}
    cfg_empty = {"poll_interval": ""}

    # Test all INFRA contexts
    for ctx in [
        Context.NF_INFRA_LOCAL.value,
        Context.NF_INFRA_HPC.value,
        Context.CUSTOM_INFRA_LOCAL.value,
        Context.CUSTOM_INFRA_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)
        # Shoudl fail
        check_config(cfg_invalid_zero, fail=True, ctx=ctx)
        check_config(cfg_invalid_str, fail=True, ctx=ctx)
        check_config(cfg_invalid_neg, fail=True, ctx=ctx)

    # Test all PIPE contexts
    for ctx in [
        Context.NF_PIPE_LOCAL.value,
        Context.NF_PIPE_HPC.value,
        Context.CUSTOM_PIPE_LOCAL.value,
        Context.CUSTOM_PIPE_HPC.value,
    ]:
        # Should succeed
        check_config(cfg_valid, fail=False, ctx=ctx)
        check_config(cfg_valid_float, fail=False, ctx=ctx)
        check_config(cfg_invalid_zero, fail=False, ctx=ctx)
        check_config(cfg_invalid_str, fail=False, ctx=ctx)
        check_config(cfg_invalid_neg, fail=False, ctx=ctx)
        check_config(cfg_empty, fail=False, ctx=ctx)
