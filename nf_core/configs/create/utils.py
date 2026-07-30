"""Config creation specific functions and classes"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from math import ceil
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, ValidationInfo, field_validator
from textual import on
from textual.app import ComposeResult
from textual.containers import Grid
from textual.suggester import SuggestFromList
from textual.validation import ValidationResult, Validator
from textual.widget import Widget
from textual.widgets import Input, RichLog, Static

# Use ContextVar to define a context on the model initialization
_init_context_var: ContextVar = ContextVar("_init_context_var", default=None)
_init_context_var.set({})


@contextmanager
def init_context(value: dict[str, Any]) -> Iterator[None]:
    token = _init_context_var.set(value)
    try:
        yield
    finally:
        _init_context_var.reset(token)


# Define a global variable to store the config type
CONFIG_ISINFRASTRUCTURE_GLOBAL: bool = True
NFCORE_CONFIG_GLOBAL: bool = True
INFRA_ISHPC_GLOBAL: bool = False
_PATH_PATTERN = re.compile(r"(\/|~\/|~$|\$\{?\w+\}?)(.*)")
# Used by finalinfradetails as it already imports create.utils
SUPPORTED_CONTAINERS = ["singularity", "docker", "apptainer", "charliecloud", "podman", "sarus", "shifter", "conda"]
CACHED_CONTAINERS = ["singularity", "apptainer", "charliecloud", "conda"]
SUPPORTED_SCHEDULERS = ["local", "pbs", "pbspro", "slurm", "sge", "nqsii", "lsf", "moab", "condor", "hyperqueue", "flux", "tcs"]
SUPPORTED_DIRECTIVES = {
    "local": ["cpus", "memory", "time"],
    "lsf": ["cpus", "memory", "time", "queue"],
    "moab": ["cpus", "memory", "time", "queue"],
    "nqsii": ["cpus", "memory", "time", "queue"],
    "pbs": ["cpus", "memory", "time", "queue"],
    "pbspro": ["cpus", "memory", "time", "queue"],
    "sge": ["cpus", "memory", "time", "queue"],
    "slurm": ["cpus", "memory", "time", "queue"],
    "condor": ["cpus", "memory", "time"],
    "hyperqueue": ["cpus", "memory", "time"],
    "flux": ["cpus", "time", "queue"],
    "tcs": ["time"],
}


class ConfigsCreateConfig(BaseModel):
    """Pydantic model for the nf-core configs create config."""

    is_infrastructure: bool | None = False
    """ Config variable to define if this is infrastructure or pipeline """
    config_pipeline_name: str | None = None
    """ The name of the pipeline """
    config_pipeline_path: str | None = None
    """ The path to the pipeline """
    general_config_name: str | None = None
    """ Config name """
    config_profile_contact: str | None = None
    """ Config contact name """
    config_profile_handle: str | None = None
    """ Config contact GitHub handle """
    config_profile_description: str | None = None
    """ Config description """
    config_profile_url: str | None = None
    """ Config institution URL """
    default_process_ncpus: str | None = None
    """ Default number of CPUs """
    default_process_memgb: str | None = None
    """ Default amount of memory """
    default_process_hours: str | None = None
    """ Default walltime - hours """
    custom_process_name_id: str | None = None
    """" Name of a process to configure """
    custom_process_label_id: str | None = None
    """" Label of a process to configure """
    custom_process_ncpus: str | None = None
    """ Number of CPUs for process """
    custom_process_memgb: str | None = None
    """ Amount of memory for process """
    custom_process_hours: str | None = None
    """ Walltime for process - hours """
    custom_process_queue: str | None = None
    """ Custom queue for process to override default """
    named_process_resources: dict | None = None
    """ Dictionary containing custom resource requirements for named processes """
    labelled_process_resources: dict | None = None
    """ Dictionary containing custom resource requirements for labelled processes """
    is_nfcore: bool | None = None
    """ Whether the config is part of the nf-core organisation """
    savelocation: str | None = None
    """ Final location of the configuration file """
    scheduler: str | None = None
    """ The scheduler that the HPC uses """
    queue: str | None = None
    """ The default queue that the HPC uses """
    module_system: str | None = None
    """ Modules to load when running processes """
    container_system: str | None = None
    """ The container system the HPC uses """
    memory: str | None = None
    """ The maximum memory available to processes """
    cpus: str | None = None
    """ The maximum number of CPUs available to processes """
    time: str | None = None
    """ The maximum walltime available to processes """
    cachedir: str | None = None
    """ An environment variable to hold a custom Nextflow container cachedir """
    igenomes_cachedir: str | None = None
    """ A cachedir for iGenomes """
    scratch_dir: str | None = None
    """ A scratch directory to use """
    retries: str | None = None
    """ Number of retries for failed jobs """
    module: bool | None = False
    """ Whether the infrastructure uses a module system """
    delete_work_dir: bool | None = False
    """ Whether to clean up the work directory upon successful completion """
    queue_stat_interval: str | None = None
    """ How often to check the HPC queue status. """
    queue_size: str | None = None
    """ How many jobs can be submitted to the queue at once. """
    poll_interval: str | None = None
    """ How often to check for successful completion of processes. """
    submit_rate: str | None = None
    """ How many jobs can be submitted per minute. """

    model_config = ConfigDict(extra="allow")

    def __init__(self, /, **data: Any) -> None:
        """Custom init method to allow using a context on the model initialization."""
        self.__pydantic_validator__.validate_python(
            data,
            self_instance=self,
            context=_init_context_var.get(),
        )

    def _remove_empty_sections(self, config_dict: dict):
        # Takes a config dict produced by serial_hpc() or serial_pipeline()
        # and removes keys with null or empty values
        ret = {}
        for k, v in config_dict.items():
            if isinstance(v, dict):
                v2 = self._remove_empty_sections(v)
            else:
                v2 = v
            if v2:
                ret[k] = v2
        return ret

    def _format_resource_request(self, value_str: str, unit_str: str) -> str:
        # Format a resource request to an integer
        # and update the units if required
        # E.g. 1.0h -> 1h; 1.0GB -> 1GB
        # and 0.5h -> 30min; 0.5GB -> 512MB

        # Make sure unit_str is valid
        assert unit_str in ["h", "min", "GB"], f'Invalid unit: "{unit_str}"'

        # Turn the value string into a float
        v = float(value_str)
        u = unit_str
        if v.is_integer():
            v = int(v)
            if v == 0:
                v = 1
        elif v < 1:
            if unit_str == "min":
                v = ceil(v * 60)
                u = "s"
            elif unit_str == "h":
                v = ceil(v * 60)
                u = "min"
            elif unit_str == "GB":
                v = ceil(v * 1024)
                u = "MB"
        return f"{v} {u}"

    def serial_params(self):
        # Determine contact info
        contact = ""
        if self.config_profile_contact:
            contact = self.config_profile_contact
            if self.config_profile_handle:
                contact += f" ({self.config_profile_handle})"
        elif self.config_profile_handle:
            contact = self.config_profile_handle
        else:
            contact = None
        ret = {
            "params": {
                "config_profile_contact": contact,
                "config_profile_description": self.config_profile_description or None,
                "config_profile_url": self.config_profile_url or None,
                "igenomes_base": self.igenomes_cachedir or None,
            },
        }
        return self._remove_empty_sections(ret)

    def serial_hpc(self):
        """Returns a dictionary of the config"""
        # Get params section
        params = self.serial_params()
        # Determine modules to load
        modules_to_load = self.container_system if self.module and self.container_system else ""
        if self.module_system:
            if modules_to_load:
                modules_to_load += " "
            modules_to_load += re.sub(r"\s+", ":", self.module_system)
        # Create resourceLimits list
        resource_limits = [
            {"cpus": int(self.cpus)} if self.cpus else None,
            {"memory": self._format_resource_request(self.memory, "GB")} if self.memory else None,
            {"time": self._format_resource_request(self.time, "h")} if self.time else None,
        ]
        resource_limits = [d for d in resource_limits if d]
        ret = {
            **params,
            "executor": {
                "queueStatInterval": self._format_resource_request(self.queue_stat_interval, "min")
                if self.queue_stat_interval
                else None,
                "queueSize": int(self.queue_size) if self.queue_size else None,
                "pollInterval": self._format_resource_request(self.poll_interval, "min")
                if self.poll_interval
                else None,
                "submitRateLimit": self._format_resource_request(self.submit_rate, "min") if self.submit_rate else None,
            },
            "process": {
                "executor": self.scheduler or None,
                "queue": self.queue or None,
                "resourceLimits": resource_limits,
                "scratch": self.scratch_dir or None,
                "maxRetries": int(self.retries) if self.retries else None,
                "module": modules_to_load or None,
            },
            self.container_system: {
                "enabled": True,
                "cacheDir": self.cachedir
                if self.container_system in CACHED_CONTAINERS
                else None,
                "autoMounts": True if self.container_system in ["singularity", "apptainer"] else None,
            },
            "cleanup": self.delete_work_dir,
        }

        return self._remove_empty_sections(ret)

    def serial_pipeline(self):
        """Returns a dictionary of the pipeline config"""
        # Get params section
        params = self.serial_params()
        ret = {
            **params,
            "process": {
                "cpus": int(self.default_process_ncpus) if self.default_process_ncpus else None,
                "memory": self._format_resource_request(self.default_process_memgb, "GB")
                if self.default_process_memgb
                else None,
                "time": self._format_resource_request(self.default_process_hours, "h")
                if self.default_process_hours
                else None,
            },
        }
        # Get custom process resources
        for selector in ["withName", "withLabel"]:
            custom_resources_dict = (
                self.named_process_resources if selector == "withName" else self.labelled_process_resources
            )
            if not custom_resources_dict:
                continue
            for process_id, process_resources in custom_resources_dict.items():
                ret["process"][f"{selector}: '{process_id}'"] = {
                    "cpus": (
                        int(process_resources["custom_process_ncpus"])
                        if process_resources["custom_process_ncpus"]
                        else None
                    ),
                    "memory": (
                        self._format_resource_request(process_resources["custom_process_memgb"], "GB")
                        if process_resources["custom_process_memgb"]
                        else None
                    ),
                    "time": (
                        self._format_resource_request(process_resources["custom_process_hours"], "h")
                        if process_resources["custom_process_hours"]
                        else None
                    ),
                }
                if "custom_process_queue" in process_resources:
                    ret["process"][f"{selector}: '{process_id}'"]["queue"] = (
                        process_resources["custom_process_queue"] if process_resources["custom_process_queue"] else None
                    )
                if "executor" in process_resources:
                    ret["process"][f"{selector}: '{process_id}'"]["executor"] = (
                        process_resources["executor"] if process_resources["executor"] else None
                    )
        return self._remove_empty_sections(ret)

    def serial(self):
        if self.is_infrastructure:
            return self.serial_hpc()
        else:
            return self.serial_pipeline()

    @field_validator("general_config_name")
    @classmethod
    def notempty(cls, v: str) -> str:
        """Check that string values are not empty."""
        if v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator("config_profile_description")
    @classmethod
    def notempty_nfcore(cls, v: str, info: ValidationInfo) -> str:
        """Check that string values are not empty."""
        context = info.context
        if context and context["is_nfcore"] and v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator("general_config_name")
    @classmethod
    def all_lower_case(cls, v: str, info: ValidationInfo) -> str:
        """Check that string values are all lower-case."""
        context = info.context
        if context and context["is_nfcore"] and not v.islower():
            raise ValueError("Config names must not contain upper-case letters.")
        return v

    @field_validator("config_pipeline_path")
    @classmethod
    def path_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that a path is valid."""
        context = info.context
        if context and not context["is_infrastructure"] and not context["is_nfcore"]:
            if v.strip() == "":
                raise ValueError("Cannot be left empty.")
            if not Path(v).is_dir():
                raise ValueError("Must be a valid path.")
        return v

    @field_validator("savelocation")
    @classmethod
    def final_path_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that the final save directory is valid."""
        if v.strip() == "":
            raise ValueError("Cannot be left empty.")
        if not Path(v).is_dir():
            raise ValueError("Must be a valid path to a directory.")
        return v

    @field_validator("config_pipeline_name")
    @classmethod
    def nfcore_name_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that an nf-core pipeline name is valid."""
        context = info.context
        if context and not context["is_infrastructure"] and context["is_nfcore"] and v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator("config_profile_contact")
    @classmethod
    def notempty_contact(cls, v: str, info: ValidationInfo) -> str:
        """Check that contact values are not empty when the config is nf-core."""
        context = info.context
        if context and context["is_nfcore"] and v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator(
        "config_profile_handle",
    )
    @classmethod
    def handle_prefix(cls, v: str, info: ValidationInfo) -> str:
        """Check that GitHub handles start with '@'.
        Make providing a handle mandatory for nf-core configs"""
        context = info.context
        if context and context["is_nfcore"]:
            if v.strip() == "":
                raise ValueError("Cannot be left empty.")
            if not re.match(r"^@[aA-zZ\d](?:[aA-zZ\d]|-(?=[aA-zZ\d])){0,38}$", v):
                ## Regex adapted from: https://github.com/shinnn/github-username-regex
                raise ValueError("Handle must start with '@'.")
        return v

    @field_validator(
        "config_profile_url",
    )
    @classmethod
    def url_prefix(cls, v: str, info: ValidationInfo) -> str:
        """Check that institutional web links start with valid URL prefix."""
        context = info.context
        if context and context["is_nfcore"]:
            if v.strip() == "":
                raise ValueError("Cannot be left empty.")
            elif not re.match(
                r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
                v,
            ):  ## Regex from: https://stackoverflow.com/a/3809435
                raise ValueError(
                    "Handle must be a valid URL starting with 'https://' or 'http://' and include the domain (e.g. .com)."
                )
        return v

    @field_validator("custom_process_name_id")
    @classmethod
    def valid_process_name(cls, v: str, info: ValidationInfo) -> str:
        """Check that the custom process name isn't empty and is valid."""
        context = info.context
        if context and not context["is_infrastructure"]:
            if v.strip() == "":
                raise ValueError("Cannot be left empty.")
            if context["is_nfcore"] and not re.match(
                r"^[A-Z0-9_:.*]+$",
                v,
            ):
                raise ValueError("Must be uppercase and contain only letters, numbers, `_`, `:`, `.`, and `*`")
        return v

    @field_validator("custom_process_label_id")
    @classmethod
    def valid_process_label(cls, v: str, info: ValidationInfo) -> str:
        """Check that the custom process label isn't empty and is valid."""
        context = info.context
        if context and not context["is_infrastructure"]:
            if v.strip() == "":
                raise ValueError("Cannot be left empty.")
            if context["is_nfcore"] and not re.match(
                r"^[a-z0-9_]+$",
                v,
            ):
                raise ValueError("Must be lowercase and contain only letters, numbers, and `_`")
        return v

    @field_validator("default_process_ncpus", "default_process_memgb", "custom_process_ncpus", "custom_process_memgb")
    @classmethod
    def pos_integer_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that integer values are either empty or positive.

        This contains the same validation as self.pos_integer_valid_infra().
        However, keep infrastructure and pipeline methods decoupled for
        easier refactoring in future.
        """
        context = info.context
        if context and not context["is_infrastructure"]:
            if v.strip() == "":
                return v
            try:
                v_int = int(v.strip())
            except ValueError:
                raise ValueError("Must be an integer.") from None
            if not v_int > 0:
                raise ValueError("Must be a positive integer.")
        return v

    @field_validator("default_process_hours", "custom_process_hours")
    @classmethod
    def non_neg_float_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that numeric values are either empty or non-negative."""
        context = info.context
        if context and not context["is_infrastructure"]:
            if v.strip() == "":
                return v
            try:
                vf = float(v.strip())
            except ValueError:
                raise ValueError("Must be a number.") from None
            if not vf >= 0:
                raise ValueError("Must be a non-negative number.")
        return v

    @field_validator("custom_process_queue")
    @classmethod
    def valid_custom_queue(cls, v: str, info: ValidationInfo) -> str:
        """Check that a custom queue is either not set or is a valid string"""
        context = info.context
        if context and not context["is_infrastructure"]:
            if v.strip() == "":
                return v
            if " " in v.strip():
                raise ValueError("Cannot contain spaces")
        # TODO: Any other invalid characters?
        return v

    @field_validator("cpus", "memory", "retries")
    @classmethod
    def pos_integer_valid_infra(cls, v: str, info: ValidationInfo) -> str:
        """
        Check that integer values are positive.

        This contains the same validation as self.pos_integer_valid().
        However, keep infrastructure and pipeline methods decoupled for
        easier refactoring in future.
        """
        context = info.context
        if context and context["is_infrastructure"]:
            if v.strip() == "":
                raise ValueError("Cannot be empty.")
            try:
                v_int = int(v.strip())
            except ValueError:
                raise ValueError("Must be an integer.") from None
            if not v_int > 0:
                raise ValueError("Must be a positive integer.")
        return v

    @field_validator("queue_size", "submit_rate")
    @classmethod
    def pos_integer_optional_valid_infra(cls, v: str, info: ValidationInfo) -> str:
        """
        Check that integer values are either empty or positive.

        This contains the same validation as self.pos_integer_valid_infra(),
        but allows for empty values as well
        """
        context = info.context
        if context and context["is_infrastructure"]:
            if v.strip() == "":
                return v
            try:
                v_int = int(v.strip())
            except ValueError:
                raise ValueError("Must be an integer.") from None
            if not v_int > 0:
                raise ValueError("Must be a positive integer.")
        return v

    @field_validator("time")
    @classmethod
    def non_neg_float_valid_infra(cls, v: str, info: ValidationInfo) -> str:
        """Check that numeric values are either empty or non-negative."""
        context = info.context
        if context and context["is_infrastructure"]:
            if v.strip() == "":
                raise ValueError("Cannot be empty.")
            try:
                vf = float(v.strip())
            except ValueError:
                raise ValueError("Must be a number.") from None
            if not vf >= 0:
                raise ValueError("Must be a non-negative number.")
        return v

    @field_validator("poll_interval")
    @classmethod
    def pos_float_valid_infra(cls, v: str, info: ValidationInfo) -> str:
        """Check that numeric values are positive."""
        context = info.context
        if context and context["is_infrastructure"]:
            if v.strip() == "":
                return v
            try:
                vf = float(v.strip())
            except ValueError:
                raise ValueError("Must be a number.") from None
            if not vf > 0:
                raise ValueError("Must be a positive number.")
        return v

    @field_validator("scheduler")
    @classmethod
    def nonemtpy_hpc_details(cls, v: str, info: ValidationInfo) -> str:
        """Check that HPC infrastructure details are non-empty"""
        context = info.context
        if context and context["is_infrastructure"] and context["is_hpc"] and v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator("scheduler")
    @classmethod
    def valid_scheduler(cls, v: str, info: ValidationInfo) -> str:
        """Check that the HPC scheduler is supported"""
        context = info.context
        if context and context["is_infrastructure"] and context["is_hpc"] and v.strip() not in SUPPORTED_SCHEDULERS:
            raise ValueError(f"Must be one of: {', '.join(SUPPORTED_SCHEDULERS)}")
        return v

    @field_validator("cachedir", "scratch_dir")
    @classmethod
    def is_path_ondisk(cls, v: str, info: ValidationInfo) -> str:
        """
        Check that a path looks valid. Does not check if it exists.

        Skip if field is empty.

        Accept:
            - absolute paths (^/.+)
            - env var prefixed paths (${INFRA_SPECIFIC_VAR}/..., ${HOME}/..., ${projectDir})
            - tilde-prefixed paths (~/...)
        """
        v = v.strip()
        if v == "":
            return v  # optional

        if not _PATH_PATTERN.match(v):
            raise ValueError(
                "Must be an absolute path (/data/scratch), "
                "a path relative to home (~/scratch), "
                "or a path with an environmental variable (e.g. ${DIR}/scratch)"
            )
        return v

    @field_validator("igenomes_cachedir")
    @classmethod
    def is_path_or_uri(cls, v: str, info: ValidationInfo) -> str:
        v = v.strip()
        if v == "":
            return v  # optional

        uri_pattern = re.compile(r"^\w+:\/\/\w+")
        if not _PATH_PATTERN.match(v) and not uri_pattern.match(v):
            raise ValueError(
                "Must be an absolute path with optional environmental variables "
                "(e.g. /data/cache, ~/cache, ${DIR}/cache), "
                "or a URI (e.g. s3://ngi-igenomes/igenomes/)"
            )
        return v

    @field_validator("container_system")
    @classmethod
    def container_system_valid(cls, v: str, info: ValidationInfo) -> str:
        v = v.strip()
        if v != "" and v not in SUPPORTED_CONTAINERS:
            raise ValueError(f"Must be one of: {', '.join(SUPPORTED_CONTAINERS)}")
        return v

    @field_validator("queue_stat_interval")
    @classmethod
    def pos_hpc_interval_valid(cls, v: str, info: ValidationInfo) -> str:
        """Check that HPC interval values are positive."""
        context = info.context
        if context and context["is_infrastructure"] and context["is_hpc"]:
            if v.strip() == "":
                return v
            try:
                vf = float(v.strip())
            except ValueError:
                raise ValueError("Must be a number.") from None
            if not vf > 0:
                raise ValueError("Must be a positive number.")
        return v


## TODO Duplicated from pipelines utils - move to common location if possible (validation seems to be context specific so possibly not)
class TextInput(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with help text
    and validation messages.
    """

    def __init__(
        self, field_id, placeholder, description, default=None, password=None, suggestions=None, **kwargs
    ) -> None:
        """Initialise the widget with our values.

        Pass on kwargs upstream for standard usage."""
        super().__init__(**kwargs)
        self.field_id: str = field_id
        self.id: str = field_id
        self.placeholder: str = placeholder
        self.description: str = description
        self.default: str = default
        self.password: bool = password
        self.suggestions: list[str] = suggestions or []

    def compose(self) -> ComposeResult:
        yield Grid(
            Static(self.description, classes="field_help"),
            Input(
                placeholder=self.placeholder,
                validators=[ValidateConfig(self.field_id)],
                value=self.default,
                password=self.password,
                suggester=SuggestFromList(self.suggestions, case_sensitive=False),
            ),
            Static(classes="validation_msg"),
            classes="text-input-grid",
        )

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_invalid_reasons(self, event: Input.Changed | Input.Submitted) -> None:
        """Validate the text input and show errors if invalid."""
        val_msg = self.query_one(".validation_msg")
        if not isinstance(val_msg, Static):
            raise ValueError("Validation message not found.")

        if event.validation_result is not None and not event.validation_result.is_valid:
            # check that val_msg is instance of Static
            if isinstance(val_msg, Static):
                val_msg.update("\n".join(event.validation_result.failure_descriptions))
        else:
            val_msg.update("")


## TODO Duplicated from pipelines utils - move to common location if possible (validation seems to be context specific so possibly not)
class ValidateConfig(Validator):
    """Validate any config value, using Pydantic."""

    def __init__(self, key) -> None:
        """Initialise the validator with the model key to validate."""
        super().__init__()
        self.key = key

    def validate(self, value: str) -> ValidationResult:
        """Try creating a Pydantic object with this key set to this value.

        If it fails, return the error messages."""
        try:
            with init_context(
                {
                    "is_nfcore": NFCORE_CONFIG_GLOBAL,
                    "is_infrastructure": CONFIG_ISINFRASTRUCTURE_GLOBAL,
                    "is_hpc": INFRA_ISHPC_GLOBAL,
                }
            ):
                ConfigsCreateConfig(**{f"{self.key}": value})
                return self.success()
        except ValidationError as e:
            return self.failure(", ".join([err["msg"] for err in e.errors()]))


def generate_config_entry(self, key, value):
    parsed_entry = "  " + key + ' = "' + value + '"\n'
    return parsed_entry


class LoggingConsole(RichLog):
    file = False
    console: Widget

    def print(self, content):
        self.write(content)


def add_hide_class(app, widget_id: str) -> None:
    """Add class 'hide' to a widget. Not display widget."""
    app.get_widget_by_id(widget_id).add_class("hide")


def remove_hide_class(app, widget_id: str) -> None:
    """Remove class 'hide' to a widget. Display widget."""
    app.get_widget_by_id(widget_id).remove_class("hide")
