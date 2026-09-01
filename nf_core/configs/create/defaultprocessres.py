"""Get information about which process/label the user wants to configure."""

from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown

from nf_core.configs.create.utils import ConfigsCreateConfig, TextInput, init_context

markdown_explain = """
Use the following fields to specify the **default** number of
CPUs, memory (in GB) and walltime (in hours) for your pipeline.

These values will be used by any process that haven't been specifically configured
to request a particular resource. For example, if a process is configured to
request 2 CPUs and 8GB of memory, but no walltime is specified,
the walltime value below will be used.

All values are optional, but recommended.

Use the `Skip` button to skip setting default resource values.
"""


class DefaultProcess(Screen):
    """Get default process resource requirements."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Default process resources
                """
            )
        )
        yield Markdown(markdown_explain)
        yield TextInput(
            "default_process_ncpus",
            "CPUs (OPTIONAL)",
            "Number of CPUs to use by default for all processes.",
            "1",
            classes="column",
        )
        yield TextInput(
            "default_process_memgb",
            "Memory (GB) (OPTIONAL)",
            "Amount of memory in GB to use by default for all processes.",
            "2",
            classes="column",
        )
        yield TextInput(
            "default_process_hours",
            "Time (hours) (OPTIONAL)",
            "The default number of hours of walltime required for processes:",
            "1",
            classes="column",
        )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Skip", id="skip", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed, "#skip")
    def skip_to_next_screen(self) -> None:
        # Skip to the next screen without saving
        if self.parent.PIPE_CONF_NAMED:
            self.parent.push_screen("multi_named_process_config")
        elif self.parent.PIPE_CONF_LABELLED:
            self.parent.push_screen("multi_labelled_process_config")
        else:
            self.parent.push_screen("final")

    @on(Button.Pressed, "#next")
    def on_next_button(self, event: Button.Pressed) -> None:
        """Save fields to the config."""
        new_config = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            validation_result = this_input.validate(this_input.value)
            new_config[text_input.field_id] = this_input.value
            if not validation_result.is_valid:
                text_input.query_one(".validation_msg").update("\n".join(validation_result.failure_descriptions))
            else:
                text_input.query_one(".validation_msg").update("")
        try:
            with init_context(self.parent.get_context()):
                # Validate and save the new config data
                ConfigsCreateConfig(**new_config)
                self.parent.TEMPLATE_CONFIG["default_process"] = new_config
            # Push the next screen
            if self.parent.PIPE_CONF_NAMED:
                self.parent.push_screen("multi_named_process_config")
            elif self.parent.PIPE_CONF_LABELLED:
                self.parent.push_screen("multi_labelled_process_config")
            else:
                self.parent.push_screen("final")
        except ValueError:
            pass

    @on(Button.Pressed, "#back")
    def on_back_button(self, event: Button.Pressed) -> None:
        """Clear the default config info"""
        self.parent.TEMPLATE_CONFIG.pop("basic_details", None)
