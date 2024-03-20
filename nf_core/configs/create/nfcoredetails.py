"""A Textual app to create a config."""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.utils import TextInputWithHelp


class NfcoreDetails(Screen):
    """Name, description, author, etc."""

    ## This allows dynamic updating of different fields, to add additional 'live' updates:
    ## extend function by copy updating `query_one` commands
    def on_input_changed(self, event: Input.Changed):
        ## Retrieve input keys
        input_config = self.query_one("#config_name", TextInputWithHelp)
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
                # Details for nf-core configs
                """
            )
        )
        with Horizontal():
            yield TextInputWithHelp(
                "config_name",
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
            "handle",
            "@OctoCat",
            "Github handle of the main author / authors",
            "Long form help text goes here",
        )

        yield TextInputWithHelp(
            "description",
            "Config built by nf-core/tools.",
            "A short description of your config.",
            "Long form help text goes here",
        )

        yield TextInputWithHelp(
            "institute_url",
            "https://nf-co.re",
            "URL to institution hosting the infrastructure (e.g. HPC)",
            "Long form help text goes here",
        )

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="nfcoredetails_continue", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInputWithHelp"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")

        self.parent.TEMPLATE_CONFIG.__dict__.update({"config_name": self.query_one("#config_name", TextInputWithHelp)})
        self.parent.LOGGING_STATE = "pipeline created"
