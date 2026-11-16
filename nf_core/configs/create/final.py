from textual import on
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.create import ConfigCreate
from nf_core.configs.create.utils import ConfigsCreateConfig, TextInput, init_context


class FinalScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            """
# Final step
"""
        )
        yield TextInput(
            "savelocation",
            ".",
            "In which directory would you like to save the config?",
            ".",
            classes="row",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Save and close!", id="close_app", variant="success"),
            classes="cta",
        )

    def _create_config(self, config_dir=".") -> None:
        """Create the config."""
        # Merge the configs from each screen into one
        final_config = {}
        for tmp_config in self.parent.TEMPLATE_CONFIG.values():
            final_config.update(tmp_config)
        create_obj = ConfigCreate(
            template_config=ConfigsCreateConfig(**final_config),
            config_type=self.parent.CONFIG_TYPE,
            config_dir=config_dir,
        )
        create_obj.write_to_file()

    @on(Button.Pressed, "#close_app")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        # Validate the save location
        save_location = self.query_one("TextInput")
        save_location_text = save_location.query_one(Input)
        try:
            with init_context(self.parent.get_context()):
                ConfigsCreateConfig(savelocation=save_location_text.value)
            # If validation passes, create the config
            self._create_config(config_dir=save_location_text.value)
            self.parent.close_app()
        except ValueError:
            pass
