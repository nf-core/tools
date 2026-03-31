"""A Textual app to create a pipeline."""

from pathlib import Path
from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.pipelines.create.utils import CreateConfig, TextInput, add_hide_class, remove_hide_class
from nf_core.utils import get_org_url

pipeline_exists_warn = """
> ⚠️  **The pipeline you are trying to create already exists.**
>
> If you continue, you will **override** the existing pipeline.
> Please change the pipeline or organisation name to create a different pipeline.
"""


class BasicDetails(Screen):
    """Name, description, author, etc."""

    _auto_org_full_name: str | None = None
    _auto_org_url: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Basic details
                """
            )
        )
        with Horizontal():
            yield TextInput(
                "org",
                "Organisation",
                "GitHub organisation",
                "nf-core",
                classes="column",
                disabled=self.parent.NFCORE_PIPELINE,
            )
            yield TextInput(
                "name",
                "Pipeline Name",
                "Workflow name",
                classes="column",
            )

        yield TextInput(
            "description",
            "Description",
            "A short description of your pipeline.",
        )
        yield TextInput(
            "author",
            "Author(s)",
            "Name of the main author / authors",
        )
        if not self.parent.NFCORE_PIPELINE:
            yield TextInput(
                "org_full_name",
                "Organisation Name",
                "Display name for the organisation",
                "nf-core",
            )
            yield TextInput(
                "org_url",
                "Organisation URL",
                "Website URL for the organisation",
                get_org_url("nf-core", self.parent.NFCORE_PIPELINE),
            )
        yield Markdown(dedent(pipeline_exists_warn), id="exist_warn", classes="hide")
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    def _sync_org_metadata_inputs(self, force: bool = False) -> None:
        """Keep organisation metadata in sync with the org value until the user overrides it."""
        if self.parent.NFCORE_PIPELINE:
            return

        org_input = self._get_input_widget("org")
        org_full_name_input = self._get_input_widget("org_full_name")
        org_url_input = self._get_input_widget("org_url")
        suggested_name = org_input.value or "nf-core"
        suggested_url = get_org_url(org_input.value or "nf-core", self.parent.NFCORE_PIPELINE)

        if force or org_full_name_input.value in {"", self._auto_org_full_name}:
            org_full_name_input.value = suggested_name

        if force or org_url_input.value in {"", self._auto_org_url}:
            org_url_input.value = suggested_url

        self._auto_org_full_name = suggested_name
        self._auto_org_url = suggested_url

    def _get_input_widget(self, field_id: str) -> Input:
        """Return the inner Textual input for a named TextInput wrapper."""
        return self.query_one(f"#{field_id}", TextInput).query_one(Input)

    def _get_config_values(self) -> dict[str, str]:
        """Collect screen values and inject nf-core defaults for hidden fields."""
        config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            config[text_input.field_id] = this_input.value

        if self.parent.NFCORE_PIPELINE:
            # Add nf-core defaults for hidden fields, to avoid errors when creating a pipeline
            config["org_full_name"] = config["org"]
            config["org_url"] = get_org_url("nf-core", True)

        return config

    @on(Input.Changed)
    @on(Input.Submitted)
    def show_exists_warn(self, event: Input.Changed | Input.Submitted) -> None:
        """Check if the pipeline exists on every input change or submitted.
        If the pipeline exists, show warning message saying that it will be overridden."""
        if event.input is self._get_input_widget("org"):
            self._sync_org_metadata_inputs()
        config = self._get_config_values()
        if Path(config["org"] + "-" + config["name"]).is_dir():
            remove_hide_class(self.parent, "exist_warn")
        else:
            add_hide_class(self.parent, "exist_warn")

    @on(Input.Blurred)
    def restore_empty_org_metadata_on_blur(self, event: Input.Blurred) -> None:
        """Restore auto-managed org metadata only after the user leaves the field empty."""
        if self.parent.NFCORE_PIPELINE:
            return

        org_input = self._get_input_widget("org")
        for field_id in ("org_full_name", "org_url"):
            if event.input is self._get_input_widget(field_id):
                if event.input.value:
                    break
                if field_id == "org_full_name":
                    restored_value = org_input.value or "nf-core"
                    self._auto_org_full_name = restored_value
                else:
                    restored_value = get_org_url(org_input.value or "nf-core", self.parent.NFCORE_PIPELINE)
                    self._auto_org_url = restored_value
                event.input.value = restored_value
                break

    def on_screen_resume(self):
        """Hide warn message on screen resume.
        Update displayed value on screen resume."""
        add_hide_class(self.parent, "exist_warn")
        for text_input in self.query("TextInput"):
            if text_input.field_id == "org":
                text_input.disabled = self.parent.NFCORE_PIPELINE
        self._sync_org_metadata_inputs(force=True)

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        config = self._get_config_values()
        try:
            self.parent.TEMPLATE_CONFIG = CreateConfig(**config)
            if event.button.id == "next":
                if self.parent.NFCORE_PIPELINE:
                    self.parent.push_screen("type_nfcore")
                else:
                    self.parent.push_screen("type_custom")
        except ValueError:
            pass
