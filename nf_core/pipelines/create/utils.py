import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator
from textual import on
from textual.app import ComposeResult
from textual.validation import ValidationResult, Validator
from textual.widgets import Input, Static


class CreateConfig(BaseModel):
    """Pydantic model for the nf-core create config."""

    org: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    version: Optional[str] = None
    force: Optional[bool] = None
    outdir: Optional[str] = None
    skip_features: Optional[list] = None
    is_nfcore: Optional[bool] = None

    model_config = ConfigDict(extra="allow")

    @field_validator("name")
    @classmethod
    def name_nospecialchars(cls, v: str) -> str:
        """Check that the pipeline name is simple."""
        if not re.match(r"^[a-z]+$", v):
            raise ValueError("Must be lowercase without punctuation.")
        return v

    @field_validator("org", "description", "author", "version")
    @classmethod
    def notempty(cls, v: str) -> str:
        """Check that string values are not empty."""
        if v.strip() == "":
            raise ValueError("Cannot be left empty.")
        return v

    @field_validator("version")
    @classmethod
    def version_nospecialchars(cls, v: str) -> str:
        """Check that the pipeline version is simple."""
        if not re.match(r"^([0-9]+)(\.?([0-9]+))*(dev)?$", v):
            raise ValueError(
                "Must contain at least one number, and can be prefixed by 'dev'. Do not use a 'v' prefix or spaces."
            )
        return v


class TextInput(Static):
    """Widget for text inputs.

    Provides standard interface for a text input with help text
    and validation messages.
    """

    def __init__(self, field_id, placeholder, description, default=None, **kwargs) -> None:
        """Initialise the widget with our values.

        Pass on kwargs upstream for standard usage."""
        super().__init__(**kwargs)
        self.field_id: str = field_id
        self.placeholder: str = placeholder
        self.description: str = description
        self.default: str = default

    def compose(self) -> ComposeResult:
        yield Static(self.description, classes="field_help")
        yield Input(
            placeholder=self.placeholder,
            validators=[ValidateConfig(self.field_id)],
            value=self.default,
        )
        yield Static(classes="validation_msg")

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_invalid_reasons(self, event: Input.Changed | Input.Submitted) -> None:
        """Validate the text input and show errors if invalid."""
        if not event.validation_result.is_valid:
            self.query_one(".validation_msg").update("\n".join(event.validation_result.failure_descriptions))
        else:
            self.query_one(".validation_msg").update("")


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
            CreateConfig(**{f"{self.key}": value})
            return self.success()
        except ValueError as e:
            return self.failure(", ".join([err["msg"] for err in e.errors()]))
