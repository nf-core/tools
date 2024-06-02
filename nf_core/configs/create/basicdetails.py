"""Get basic contact information to set in params to help with debugging. By
displaying such info in the pipeline run header on run execution"""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.utils import (
    CreateConfig,
    TextInput,
)  ## TODO Move somewhere common?

config_exists_warn = """
> ⚠️  **The config file you are trying to create already exists.**
>
> If you continue, you will **overwrite** the existing config.
> Please change the config name to create a different config!.
"""


class BasicDetails(Screen):
    """Name, description, author, etc."""

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
        ## TODO Add validation, <config_name>.conf already exists?
        yield TextInput(
            "general_config_name",
            "custom",
            "Config Name. Used for naming resulting file.",
            "",
            classes="column",
        )
        with Horizontal():
            yield TextInput(
                "profile_contact",
                "Boaty McBoatFace",
                "Author full name.",
                classes="column",
            )

            yield TextInput(
                "profile_contact_handle",
                "@BoatyMcBoatFace",
                "Author Git(Hub) handle.",
                classes="column",
            )

        yield TextInput(
            "config_profile_description",
            "Description",
            "A short description of your config.",
        )
        yield TextInput(
            "config_profile_url",
            "https://nf-co.re",
            "URL of infrastructure website or owning institution (only for infrastructure configs).",
            disabled=(
                self.parent.CONFIG_TYPE == "pipeline"
            ),  ## TODO update TextInput to accept replace with visibility: https://textual.textualize.io/styles/visibility/
        )
        ## TODO: reactivate once validation ready
        # yield Markdown(dedent(config_exists_warn), id="exist_warn", classes="hide")
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    ## TODO: update functions
    # @on(Input.Changed)
    # @on(Input.Submitted)
    # def show_exists_warn(self):
    #     """Check if the pipeline exists on every input change or submitted.
    #     If the pipeline exists, show warning message saying that it will be overriden."""
    #     config = {}
    #     for text_input in self.query("TextInput"):
    #         this_input = text_input.query_one(Input)
    #         config[text_input.field_id] = this_input.value
    #     if Path(config["org"] + "-" + config["name"]).is_dir():
    #         remove_hide_class(self.parent, "exist_warn")
    #     else:
    #         add_hide_class(self.parent, "exist_warn")

    # def on_screen_resume(self):
    #     """Hide warn message on screen resume.
    #     Update displayed value on screen resume."""
    #     add_hide_class(self.parent, "exist_warn")
    #     for text_input in self.query("TextInput"):
    #         if text_input.field_id == "org":
    #             text_input.disabled = self.parent.CONFIG_TYPE == "infrastructure"

    ## Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the CreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update(
                    "\n".join(validation_result.failure_descriptions)
                )
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            self.parent.TEMPLATE_CONFIG = CreateConfig(**config)
        except ValueError:
            pass
