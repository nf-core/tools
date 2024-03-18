"""A Textual app to create a pipeline."""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.utils import CreateConfig, TextInputWithHelp


class BasicDetails(Screen):
    """Name, description, author, etc."""

    ## This allows dynamic updating of different fields, to add additional 'live' updates:
    ## extend function by copy updating `query_one` commands
    def on_input_changed(self, event: Input.Changed):
        ## Retrieve input keys
        input_config = self.query_one("#configname", TextInputWithHelp)
        default_config = input_config.query_one(Input).value

        ## Extract existing field for updating, and modify update
        description_to_populate = self.query_one("#description", TextInputWithHelp)
        description_to_populate.query_one(Input).value = (
            default_config + " infrastructure config created with nf-core/tools."
        )

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
            yield TextInputWithHelp(
                "configname",
                "The name of the config, as would be called from the Nextflow command-line `-profile`. Typically lower case, no spaces. E.g. uppmax.",
                "Config Name",
                "Long form help text goes here",
                classes="row",
            )

        yield TextInputWithHelp(
            "author",
            "Author(s)",
            "Name of the main author / authors",
            "Long form help text goes here",
        )

        yield TextInputWithHelp(
            "description",
            "Config built by nf-core/tools.",
            "A short description of your config.",
            "Long form help text goes here",
        )

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            self.parent.TEMPLATE_CONFIG = CreateConfig(**config)
            if event.button.id == "next":
                if self.parent.CONFIGS_TYPE == "infrastructure":
                    self.parent.push_screen("type_infrastructure")
                elif self.parent.CONFIGS_TYPE == "pipeline":
                    self.parent.push_screen("type_custom")
        except ValueError:
            pass
