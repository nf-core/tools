from textual import on
from textual.app import ComposeResult
from textual.containers import Center, HorizontalScroll, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static, Switch


class NfcorePipeline(Screen):
    """Select if the pipeline will use genomic data."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        # TODO: add features to customise the pipeline template
        yield Center(
            Button("Done", id="done", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed, "#done")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        skip = []
        for feature_input in self.query("PipelineFeature"):
            this_switch = feature_input.query_one(Switch)
            if not this_switch.value:
                skip.append(this_switch.id)
        self.parent.TEMPLATE_CONFIG.skip_features = skip
        self.parent.TEMPLATE_CONFIG.is_nfcore = True
