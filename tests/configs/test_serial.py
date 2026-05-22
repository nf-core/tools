from nf_core.configs.create.serial import NextflowSerial
from nf_core.configs.create.utils import ConfigsCreateConfig, init_context
from nf_core.configs.create.create import ConfigCreate

from ..test_configs import (
    INFRA_SINGULARITY_CONFIG,
    INFRA_CUSTOM_SINGULARITY_CONFIG,
    PIPE_NFCORE_CONFIG,
    PIPE_CUSTOM_CONFIG,
    INFRA_NFCORE_SINGULARITY_LOCAL_CONFIG,
    INFRA_CUSTOM_SINGULARITY_LOCAL_CONFIG,
)

from pydantic import ValidationError
from pathlib import Path
from tempfile import TemporaryDirectory

# Valid configs

VALID_NFCORE_INFRA_HPC_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": True,
    "is_nfcore": True,
    "config_profile_contact": "my name",
    "config_profile_handle": "@myhandle",
    "config_profile_description": "A cool description",
    "config_profile_url": "https://example.com",
    "scheduler": "pbspro",
    "queue": "myqueue",
    "module": False,
    "module_system": "",
    "container_system": "singularity",
    "cpus": "48",
    "memory": "128",
    "time": "9.5",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "igenomes_cachedir": "/data/igenomes/cache",
    "retries": "2",
    "delete_work_dir": True,
    "queue_stat_interval": "0.75",
    "poll_interval": "0.25",
    "queue_size": "200",
    "submit_rate": "25",
    "savelocation": ".",
}


VALID_CUSTOM_INFRA_HPC_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": True,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "scheduler": "pbspro",
    "queue": "myqueue",
    "module": False,
    "module_system": "",
    "container_system": "singularity",
    "cpus": "48",
    "memory": "128",
    "time": "9.5",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "retries": "2",
    "delete_work_dir": True,
    "queue_stat_interval": "0.75",
    "poll_interval": "0.25",
    "queue_size": "200",
    "submit_rate": "25",
    "savelocation": ".",
}


VALID_NFCORE_INFRA_LOCAL_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": True,
    "is_nfcore": True,
    "config_profile_contact": "my name",
    "config_profile_handle": "@myhandle",
    "config_profile_description": "A cool description",
    "config_profile_url": "https://example.com",
    "container_system": "singularity",
    "cpus": "8",
    "memory": "32",
    "time": "19.5",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "igenomes_cachedir": "/data/igenomes/cache",
    "retries": "2",
    "delete_work_dir": True,
    "savelocation": ".",
}


VALID_CUSTOM_INFRA_LOCAL_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": True,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "container_system": "singularity",
    "cpus": "8",
    "memory": "32",
    "time": "19.5",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "retries": "2",
    "delete_work_dir": True,
    "savelocation": ".",
}


VALID_NFCORE_PIPE_HPC_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": False,
    "is_nfcore": True,
    "config_pipeline_name": "rnaseq",
    "config_profile_contact": "my name",
    "config_profile_handle": "@myhandle",
    "config_profile_description": "A cool description",
    "config_profile_url": "https://example.com",
    "default_process_ncpus": "2",
    "default_process_memgb": "8",
    "default_process_hours": "9.5",
    "named_process_resources": {
        "SOME:PROC.NAME*": {
            "custom_process_name_id": "SOME:PROC.NAME*",
            "custom_process_ncpus": "3",
            "custom_process_memgb": "4",
            "custom_process_hours": "5.5",
            "custom_process_queue": "",
        },
        "ANOTHER:PROC_NAME": {
            "custom_process_name_id": "ANOTHER:PROC_NAME",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "3",
            "custom_process_hours": "4.4",
            "custom_process_queue": "customqueue",
        },
    },
    "labelled_process_resources": {
        "some_proc_label": {
            "custom_process_label_id": "some_proc_label",
            "custom_process_ncpus": "1",
            "custom_process_memgb": "1",
            "custom_process_hours": "1.1",
            "custom_process_queue": "",
        },
        "another_label": {
            "custom_process_label_id": "another_label",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "2",
            "custom_process_hours": "2.2",
            "custom_process_queue": "customqueue",
        },
        "a_third_label": {
            "custom_process_label_id": "a_third_label",
            "custom_process_ncpus": "",
            "custom_process_memgb": "",
            "custom_process_hours": "",
            "custom_process_queue": "",
        },
        "fourth_label": {
            "custom_process_label_id": "fourth_label",
            "custom_process_ncpus": "4",
            "custom_process_memgb": "",
            "custom_process_hours": "4.4",
            "custom_process_queue": "anotherqueue",
        },
    },
    "savelocation": ".",
}


VALID_CUSTOM_PIPE_HPC_CONFIG = {
    "general_config_name": "myconfig",
    "is_infrastructure": False,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "config_pipeline_path": ".",
    "default_process_ncpus": "2",
    "default_process_memgb": "8",
    "default_process_hours": "9.5",
    "named_process_resources": {
        "some_proc": {
            "custom_process_name_id": "some_proc",
            "custom_process_ncpus": "3",
            "custom_process_memgb": "4",
            "custom_process_hours": "5.5",
            "custom_process_queue": "",
        },
        "another_proc": {
            "custom_process_name_id": "another_proc",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "3",
            "custom_process_hours": "4.4",
            "custom_process_queue": "customqueue",
        },
    },
    "labelled_process_resources": {
        "some_proc_label": {
            "custom_process_label_id": "some_proc_label",
            "custom_process_ncpus": "1",
            "custom_process_memgb": "1",
            "custom_process_hours": "1.1",
            "custom_process_queue": "",
        },
        "another_label": {
            "custom_process_label_id": "another_label",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "2",
            "custom_process_hours": "2.2",
            "custom_process_queue": "customqueue",
        },
        "a_third_label": {
            "custom_process_label_id": "a_third_label",
            "custom_process_ncpus": "",
            "custom_process_memgb": "",
            "custom_process_hours": "",
            "custom_process_queue": "",
        },
        "fourth_label": {
            "custom_process_label_id": "fourth_label",
            "custom_process_ncpus": "4",
            "custom_process_memgb": "",
            "custom_process_hours": "4.4",
            "custom_process_queue": "anotherqueue",
        },
    },
    "savelocation": ".",
}


# Invalid configs

INVALID_NFCORE_INFRA_HPC_CONFIG = {
    "is_infrastructure": True,
    "is_nfcore": True,
    "config_profile_contact": "my name",
    "config_profile_handle": "bad handle",
    "config_profile_description": "A cool description",
    "scheduler": "unsupported",
    "queue": "myqueue",
    "module": False,
    "module_system": "",
    "container_system": "noncontainer",
    "cpus": "1.1",
    "memory": "128.9",
    "time": "9.5a",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "igenomes_cachedir": "/data/igenomes/cache",
    "retries": "2",
    "delete_work_dir": True,
    "queue_stat_interval": "0.75",
    "poll_interval": "0.25",
    "queue_size": "200",
    "submit_rate": "25",
    "savelocation": ".",
}


INVALID_CUSTOM_INFRA_HPC_CONFIG = {
    "is_infrastructure": True,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "scheduler": "pbsprose",
    "queue": "",
    "module": False,
    "module_system": "",
    "container_system": "singularitay",
    "cachedir": "singularity/cachedir",
    "scratch_dir": "tmp/scratch",
    "retries": "2",
    "delete_work_dir": True,
    "queue_stat_interval": "0.75",
    "poll_interval": "0.25",
    "queue_size": "200",
    "submit_rate": "25",
    "savelocation": ".",
}


INVALID_NFCORE_INFRA_LOCAL_CONFIG = {
    "is_infrastructure": True,
    "is_nfcore": True,
    "config_profile_contact": "my name",
    "config_profile_handle": "@myhandle",
    "config_profile_description": "A cool description",
    "config_profile_url": "bad_url",
    "container_system": "",
    "cpus": "8",
    "memory": "32",
    "time": "19.5",
    "cachedir": "/singularity/cachedir",
    "scratch_dir": "/tmp/scratch",
    "igenomes_cachedir": "/data/igenomes/cache",
    "retries": "2",
    "delete_work_dir": True,
    "savelocation": "_path_doesnt_exist_",
}


INVALID_CUSTOM_INFRA_LOCAL_CONFIG = {
    "is_infrastructure": True,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "container_system": "apptianer",
    "cpus": "8.0",
    "memory": "32 GB",
    "time": "19.5.1",
    "cachedir": "singularity/cachedir",
    "scratch_dir": "tmp/scratch",
    "retries": "2",
    "delete_work_dir": True,
    "savelocation": ".",
}


INVALID_NFCORE_PIPE_HPC_CONFIG = {
    "is_infrastructure": False,
    "is_nfcore": True,
    "config_pipeline_name": "",
    "config_profile_contact": "my name",
    "config_profile_handle": "@myhandle",
    "config_profile_description": "A cool description",
    "config_profile_url": "example.com",
    "default_process_ncpus": "2",
    "default_process_memgb": "8",
    "default_process_hours": "9.5",
    "named_process_resources": {
        "SOME:PROC.NAME*": {
            "custom_process_name_id": "SOME:PROC.NAME*",
            "custom_process_ncpus": "3",
            "custom_process_memgb": "4",
            "custom_process_hours": "5.5",
            "custom_process_queue": "",
        },
        "ANOTHER:PROC_NAME": {
            "custom_process_name_id": "ANOTHER:PROC_NAME",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "3",
            "custom_process_hours": "4.4",
            "custom_process_queue": "customqueue",
        },
    },
    "labelled_process_resources": {
        "some_proc_label": {
            "custom_process_label_id": "some_proc_label",
            "custom_process_ncpus": "1",
            "custom_process_memgb": "1",
            "custom_process_hours": "1.1",
            "custom_process_queue": "",
        },
        "another_label": {
            "custom_process_label_id": "another_label",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "2",
            "custom_process_hours": "2.2",
            "custom_process_queue": "custom queue",
        },
        "a_third_label": {
            "custom_process_label_id": "a_third_label",
            "custom_process_ncpus": "",
            "custom_process_memgb": "",
            "custom_process_hours": "",
            "custom_process_queue": "",
        },
        "fourth_label": {
            "custom_process_label_id": "fourth_label",
            "custom_process_ncpus": "4",
            "custom_process_memgb": "",
            "custom_process_hours": "4.4",
            "custom_process_queue": "anotherqueue",
        },
    },
    "savelocation": ".",
}


INVALID_CUSTOM_PIPE_HPC_CONFIG = {
    "is_infrastructure": False,
    "is_nfcore": False,
    "config_profile_description": "A cool description",
    "config_pipeline_path": "_this_path_doesnt_exist_",
    "default_process_ncpus": "2",
    "default_process_memgb": "8",
    "default_process_hours": ".",
    "named_process_resources": {
        "some_proc": {
            "custom_process_name_id": "some_proc",
            "custom_process_ncpus": "3",
            "custom_process_memgb": "4",
            "custom_process_hours": "5.5",
            "custom_process_queue": "",
        },
        "another_proc": {
            "custom_process_name_id": "another_proc",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "3",
            "custom_process_hours": "4.4",
            "custom_process_queue": "customqueue",
        },
    },
    "labelled_process_resources": {
        "some_proc_label": {
            "custom_process_label_id": "some_proc_label",
            "custom_process_ncpus": "1",
            "custom_process_memgb": "1",
            "custom_process_hours": "1.1",
            "custom_process_queue": "",
        },
        "another_label": {
            "custom_process_label_id": "another_label",
            "custom_process_ncpus": "2",
            "custom_process_memgb": "2",
            "custom_process_hours": "2.2",
            "custom_process_queue": "customqueue",
        },
        "a_third_label": {
            "custom_process_label_id": "a_third_label",
            "custom_process_ncpus": "",
            "custom_process_memgb": "",
            "custom_process_hours": "",
            "custom_process_queue": "",
        },
        "fourth_label": {
            "custom_process_label_id": "fourth_label",
            "custom_process_ncpus": "4",
            "custom_process_memgb": "",
            "custom_process_hours": "4.4",
            "custom_process_queue": "anotherqueue",
        },
    },
    "savelocation": "_this_path_also_doesnt_exist_",
}


def test_serial_valid_nfcore_infra_hpc():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": True,
            "is_hpc": True,
        }
    ):
        c = ConfigsCreateConfig(**VALID_NFCORE_INFRA_HPC_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == INFRA_SINGULARITY_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="infrastructure", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == INFRA_SINGULARITY_CONFIG


def test_serial_valid_custom_infra_hpc():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": True,
            "is_hpc": True,
        }
    ):
        c = ConfigsCreateConfig(**VALID_CUSTOM_INFRA_HPC_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == INFRA_CUSTOM_SINGULARITY_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="infrastructure", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == INFRA_CUSTOM_SINGULARITY_CONFIG


def test_serial_valid_nfcore_pipe_hpc():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": False,
            "is_hpc": True,
        }
    ):
        c = ConfigsCreateConfig(**VALID_NFCORE_PIPE_HPC_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == PIPE_NFCORE_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="pipeline", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == PIPE_NFCORE_CONFIG


def test_serial_valid_custom_pipe_hpc():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": False,
            "is_hpc": True,
        }
    ):
        c = ConfigsCreateConfig(**VALID_CUSTOM_PIPE_HPC_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == PIPE_CUSTOM_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="pipeline", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == PIPE_CUSTOM_CONFIG


def test_serial_valid_nfcore_infra_local():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": True,
            "is_hpc": False,
        }
    ):
        c = ConfigsCreateConfig(**VALID_NFCORE_INFRA_LOCAL_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == INFRA_NFCORE_SINGULARITY_LOCAL_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="infrastructure", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == INFRA_NFCORE_SINGULARITY_LOCAL_CONFIG


def test_serial_valid_custom_infra_local():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": True,
            "is_hpc": False,
        }
    ):
        c = ConfigsCreateConfig(**VALID_CUSTOM_INFRA_LOCAL_CONFIG)
        s = NextflowSerial.dumps(data_dict=c.serial(), drop_null=True)
        assert s == INFRA_CUSTOM_SINGULARITY_LOCAL_CONFIG

        # Test writing to file
        tmpdir = TemporaryDirectory()
        cf = ConfigCreate(template_config=c, config_type="infrastructure", config_dir=Path(tmpdir.name))
        cf.write_to_file()
        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        tmpdir.cleanup()
        assert config == INFRA_CUSTOM_SINGULARITY_LOCAL_CONFIG


# Invalid tests


def test_serial_invalid_nfcore_infra_hpc():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": True,
            "is_hpc": True,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_NFCORE_INFRA_HPC_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 6
        expected_error_msgs = {
            "Value error, Must be a number.",
            "Value error, Handle must start with '@'.",
            "Value error, Must be one of: singularity, docker, apptainer, charliecloud, podman, sarus, shifter, conda",
            "Value error, Must be one of: local, pbs, pbspro, slurm, sge",
            "Value error, Must be an integer.",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs


def test_serial_invalid_custom_infra_hpc():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": True,
            "is_hpc": True,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_CUSTOM_INFRA_HPC_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 4
        expected_error_msgs = {
            "Value error, Must be one of: singularity, docker, apptainer, charliecloud, podman, sarus, shifter, conda",
            "Value error, Must be one of: local, pbs, pbspro, slurm, sge",
            "Value error, Must be an absolute path (/data/scratch), a path relative to home (~/scratch), or a path with an environmental variable (e.g. ${DIR}/scratch)",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs


def test_serial_invalid_nfcore_pipe_hpc():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": False,
            "is_hpc": True,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_NFCORE_PIPE_HPC_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 2
        expected_error_msgs = {
            "Value error, Handle must be a valid URL starting with 'https://' or 'http://' and include the domain (e.g. .com).",
            "Value error, Cannot be left empty.",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs


def test_serial_invalid_custom_pipe_hpc():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": False,
            "is_hpc": True,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_CUSTOM_PIPE_HPC_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 3
        expected_error_msgs = {
            "Value error, Must be a valid path.",
            "Value error, Must be a number.",
            "Value error, Must be a valid path to a directory.",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs


def test_serial_invalid_nfcore_infra_local():
    with init_context(
        {
            "is_nfcore": True,
            "is_infrastructure": True,
            "is_hpc": False,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_NFCORE_INFRA_LOCAL_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 2
        expected_error_msgs = {
            "Value error, Handle must be a valid URL starting with 'https://' or 'http://' and include the domain (e.g. .com).",
            "Value error, Must be a valid path to a directory.",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs


def test_serial_invalid_custom_infra_local():
    with init_context(
        {
            "is_nfcore": False,
            "is_infrastructure": True,
            "is_hpc": False,
        }
    ):
        expected_error = None

        try:
            c = ConfigsCreateConfig(**INVALID_CUSTOM_INFRA_LOCAL_CONFIG)
        except ValidationError as e:
            expected_error = e

        assert expected_error is not None
        errors = expected_error.errors()
        assert len(errors) == 6
        expected_error_msgs = {
            "Value error, Must be a number.",
            "Value error, Must be an integer.",
            "Value error, Must be one of: singularity, docker, apptainer, charliecloud, podman, sarus, shifter, conda",
            "Value error, Must be an absolute path (/data/scratch), a path relative to home (~/scratch), or a path with an environmental variable (e.g. ${DIR}/scratch)",
        }
        assert set([e["msg"] for e in errors]) == expected_error_msgs
