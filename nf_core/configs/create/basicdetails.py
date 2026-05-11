"""Get basic contact information to set in params to help with debugging. By
displaying such info in the pipeline run header on run execution"""

from textwrap import dedent
from requests import get

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Select

from nf_core.configs.create.utils import ConfigsCreateConfig, TextInput, init_context
from nf_core.utils import add_hide_class, remove_hide_class

config_exists_warn = """
> ⚠️  **The config file you are trying to create already exists.**
>
> If you continue, you will **overwrite** the existing config.
> Please change the config name to create a different config!.
"""


class BasicDetails(Screen):
    """Name, description, author, etc."""

    def __init__(self) -> None:
        super().__init__()
        self.nf_core_pipelines = self.get_valid_nfcore_pipelines()

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
                "config_profile_contact",
                "Boaty McBoatFace",
                "Author full name.",
                classes="column hide" if self.parent.CONFIG_TYPE == "pipeline" else "column",
            )
            yield TextInput(
                "config_profile_handle",
                "@BoatyMcBoatFace",
                "Author Git(Hub) handle.",
                classes="column hide" if self.parent.CONFIG_TYPE == "pipeline" else "column",
            )
        yield Markdown(
            "Pipeline name.",
            id="config_pipeline_name_text",
            classes="hide" if self.parent.CONFIG_TYPE == "infrastructure" or not self.parent.NFCORE_CONFIG else "field_help",
        )
        yield Select(
            [(c, c) for c in self.nf_core_pipelines],
            prompt="The name of the nf-core pipeline you want to configure",
            id="config_pipeline_name",
            allow_blank=True,
            type_to_search=True,
            classes="hide" if self.parent.CONFIG_TYPE == "infrastructure" or not self.parent.NFCORE_CONFIG else "",
        )
        yield TextInput(
            "config_pipeline_path",
            "Pipeline path",
            "The path to the pipeline you want to create the config for.",
            classes="hide" if self.parent.CONFIG_TYPE == "infrastructure" or self.parent.NFCORE_CONFIG else "",
        )

        yield TextInput(
            "config_profile_description",
            "Description",
            "A short description of your config.",
        )
        yield TextInput(
            "config_profile_url",
            "https://nf-co.re",
            "URL of infrastructure website or owning institution (infrastructure configs only).",
            classes="hide" if self.parent.CONFIG_TYPE == "pipeline" else "",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    def get_valid_nfcore_pipelines(self) -> list[str]:
        url = "https://raw.githubusercontent.com/nf-core/website/refs/heads/main/public/pipeline_names.json"
        msg = "Error fetching nf-core pipeline list"
        response = get(url)
        if response.status_code != 200:
            # Allow the fetch to fail, e.g. while offline and configuring non-nf-core pipelines
            return []
        data = response.json()
        # If fetch was successful, ensure pipeline list is valid
        assert isinstance(data, dict), msg
        assert "pipeline" in data, msg
        pipelines = data["pipeline"]
        assert isinstance(pipelines, list), msg
        assert len(pipelines) > 0, msg
        assert all([isinstance(p, str) for p in pipelines]), msg
        return pipelines

    ## Updates the __init__ initialised TEMPLATE_CONFIG object (which is built from the ConfigsCreateConfig class) with the values from the text inputs
    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        config = {}
        for text_input in self.query("TextInput"):
            if "hide" in text_input.classes:
                continue
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            config[text_input.field_id] = this_input.value
            config["is_infrastructure"] = self.parent.CONFIG_TYPE == "infrastructure"
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        if self.parent.NFCORE_CONFIG:
            select = self.query_one("#config_pipeline_name", Select)
            config["config_pipeline_name"] = select.value
        try:
            with init_context(self.parent.get_context()):
                self.parent.TEMPLATE_CONFIG = ConfigsCreateConfig(**config)
            if event.button.id == "next":
                if self.parent.CONFIG_TYPE == "infrastructure":
                    self.parent.push_screen("hpc_question")
                elif self.parent.CONFIG_TYPE == "pipeline":
                    self.parent.push_screen("pipeline_config_question")
        except ValueError:
            pass

    def on_screen_resume(self):
        """Show or hide form fields on resume depending on config type."""
        if self.parent.CONFIG_TYPE == "pipeline":
            add_hide_class(self.parent, "config_profile_contact")
            add_hide_class(self.parent, "config_profile_handle")
            add_hide_class(self.parent, "config_profile_url")
            if self.parent.NFCORE_CONFIG:
                remove_hide_class(self.parent, "config_pipeline_name")
                remove_hide_class(self.parent, "config_pipeline_name_text")
                add_hide_class(self.parent, "config_pipeline_path")
            else:
                remove_hide_class(self.parent, "config_pipeline_path")
                add_hide_class(self.parent, "config_pipeline_name")
                add_hide_class(self.parent, "config_pipeline_name_text")
        if self.parent.CONFIG_TYPE == "infrastructure":
            remove_hide_class(self.parent, "config_profile_contact")
            remove_hide_class(self.parent, "config_profile_handle")
            remove_hide_class(self.parent, "config_profile_url")
            add_hide_class(self.parent, "config_pipeline_name")
            add_hide_class(self.parent, "config_pipeline_name_text")
            add_hide_class(self.parent, "config_pipeline_path")
