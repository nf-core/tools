from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static, Switch

from nf_core.pipelines.create.utils import PipelineFeature


class CustomPipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Template features
                """
            )
        )
        yield Horizontal(
            Switch(id="toggle_all", value=True),
            Static("Toggle all features", classes="feature_title"),
            classes="custom_grid",
        )
        yield ScrollableContainer(id="features")

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Continue", id="continue", variant="success"),
            classes="cta",
        )

    def on_mount(self) -> None:
        for name, feature in self.parent.template_features_yml.items():
            if feature["custom_pipelines"]:
                self.query_one("#features").mount(
                    PipelineFeature(feature["help_text"], feature["short_description"], feature["description"], name)
                )
        self.query_one("#toggle_all", Switch).value = True

    @on(Button.Pressed, "#continue")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        skip = []
        for feature_input in self.query("PipelineFeature"):
            this_switch = feature_input.query_one(Switch)
            if not this_switch.value:
                skip.append(this_switch.id)
        self.parent.TEMPLATE_CONFIG.__dict__.update({"skip_features": skip, "is_nfcore": False})

    @on(Switch.Changed, "#toggle_all")
    def on_toggle_all(self, event: Switch.Changed) -> None:
        """Handle toggling all switches."""
        new_state = event.value
        for feature in self.query("PipelineFeature"):
            feature.query_one(Switch).value = new_state
