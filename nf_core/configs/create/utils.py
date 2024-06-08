"""Config creation specific functions and classes"""

import re

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Dict, Iterator, Optional, Union

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from textual import on
from textual.app import ComposeResult
from textual.validation import ValidationResult, Validator
from textual.widgets import Input, Static

# Use ContextVar to define a context on the model initialization
_init_context_var: ContextVar = ContextVar("_init_context_var", default={})


@contextmanager
def init_context(value: Dict[str, Any]) -> Iterator[None]:
    token = _init_context_var.set(value)
    try:
        yield
    finally:
        _init_context_var.reset(token)


# Define a global variable to store the config type
CONFIG_ISINFRASTRUCTURE_GLOBAL: bool = True


class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    general_config_type: str = None
    general_config_name: str = None
    config_profile_contact: str = None
    config_profile_handle: str = None
    config_profile_description: str = None
    config_profile_url: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    def __init__(self, /, **data: Any) -> None:
        """Custom init method to allow using a context on the model initialization."""
        self.__pydantic_validator__.validate_python(
            data,
            self_instance=self,
            context=_init_context_var.get(),
        )

    @field_validator(
        "general_config_name",
    )
    @classmethod
    def notempty(cls, v: str) -> str:
        """Check that string values are not empty."""
        if v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator(
        "config_profile_handle",
    )
    @classmethod
    def handle_prefix(cls, v: str) -> str:
        """Check that GitHub handles start with '@'."""
        if not re.match(
            r"^@[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,38}$", v
        ):  ## Regex from: https://github.com/shinnn/github-username-regex
            raise ValueError("Handle must start with '@'.")
        return v

    @field_validator(
        "config_profile_url",
    )
    @classmethod
    def url_prefix(cls, v: str) -> str:
        """Check that institutional web links start with valid URL prefix."""
        if not re.match(
            r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
            v,
        ):  ## Regex from: https://stackoverflow.com/a/3809435
            raise ValueError(
                "Handle must be a valid URL starting with 'https://' or 'http://' and include the domain (e.g. .com)."
            )
        return v


## TODO Duplicated from pipelines utils - move to common location if possible (validation seems to be context specific so possibly not)
class TextInput(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with help text
    and validation messages.
    """

    def __init__(
        self, field_id, placeholder, description, default=None, password=None, **kwargs
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

    def compose(self) -> ComposeResult:
        yield Static(self.description, classes="field_help")
        yield Input(
            placeholder=self.placeholder,
            validators=[ValidateConfig(self.field_id)],
            value=self.default,
            password=self.password,
        )
        yield Static(classes="validation_msg")

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_invalid_reasons(
        self, event: Union[Input.Changed, Input.Submitted]
    ) -> None:
        """Validate the text input and show errors if invalid."""
        if not event.validation_result.is_valid:
            self.query_one(".validation_msg").update(
                "\n".join(event.validation_result.failure_descriptions)
            )
        else:
            self.query_one(".validation_msg").update("")


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
            with init_context({"is_infrastructure": CONFIG_ISINFRASTRUCTURE_GLOBAL}):
                CreateConfig(**{f"{self.key}": value})
                return self.success()
        except ValidationError as e:
            return self.failure(", ".join([err["msg"] for err in e.errors()]))


def generate_config_entry(self, key, value):
    parsed_entry = "  " + key + ' = "' + value + '"\n'
    return parsed_entry
