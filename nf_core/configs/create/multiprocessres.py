"""Get information about which process/label the user wants to configure."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, HorizontalGroup, Vertical, VerticalScroll
from textual.events import Mount, ScreenResume
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static

from nf_core.configs.create.utils import ConfigsCreateConfig, TextInput, init_context

markdown_process_name = """
Use the following fields to configure the basic resource requirements
for your pipeline's processes. The only required field is the process name;
all other fields can be left blank to use the pipeline or infrastructure defaults.
"""

markdown_process_label = """
Use the following fields to configure the basic resource requirements
for your pipeline's labels. The only required field is the process label;
all other fields can be left blank to use the pipeline or infrastructure defaults.
"""

markdown_process_common = """
Use the `Add another process` button to configure additional processes.

Use the read `—` buttons to remove a process configuration from the list.
"""

markdown_skip_name = """
Use the `Skip` button to skip setting process-specific resource configurations.
"""

markdown_skip_label = """
Use the `Skip` button to skip setting label-specific resource configurations.
"""

markdown_warn_name = """
**NOTE:** Process names are **not** checked for validity.
Please verify that the name is correct before continuing.
"""

markdown_warn_label = """
**NOTE:** Process labels are **not** checked for validity.
Please verify that the label is correct before continuing.
"""


class ProcessConfig(HorizontalGroup):
    """Get resource requirements for a single process."""

    def __init__(self, selector: str, hpc: bool) -> None:
        super().__init__()
        assert selector in ["name", "label"]
        self.selector = selector
        self.hpc = hpc

    def compose(self) -> ComposeResult:
        yield TextInput(
            f"custom_process_{self.selector}_id",
            f"Process {self.selector} (REQUIRED)",
            f"Process {self.selector}:",
            "",
            classes="custom-process-id",
        )
        yield TextInput(
            "custom_process_ncpus",
            "CPUs",
            "# CPUs:",
            "",
            classes="custom-process-number",
        )
        yield TextInput(
            "custom_process_memgb",
            "Mem",
            "Memory (GB):",
            "",
            classes="custom-process-number",
        )
        yield TextInput(
            "custom_process_hours",
            "Time",
            "Walltime (hours):",
            "",
            classes="custom-process-number",
        )
        yield TextInput(
            "custom_process_queue",
            "queue name (OPTIONAL)",
            "HPC queue (optional):",
            "",
            classes=("custom-process-queue" + (" hide" if not self.hpc else "")),
        )
        with Vertical(classes="remove-process-group"):
            yield Label("Remove", id="remove-process-config", classes="field_help")
            yield Button("—", id="remove", variant="error", classes="remove-process-button")
            yield Static(classes="remove-process-group-filler")  # Filler

    @on(Button.Pressed, "#remove")
    def remove_widget(self) -> None:
        self.remove()

    def update_hpc_status(self, hpc: bool) -> None:
        self.hpc = hpc
        field_id = "custom_process_queue"
        if self.hpc:
            self.get_widget_by_id(field_id).remove_class("hide")
        else:
            self.get_widget_by_id(field_id).add_class("hide")


class MultiProcessConfig(Screen):
    """Get resource requirements for multiple processes."""

    def __init__(self, selector_type: str, config_key: str, title: str) -> None:
        super().__init__()
        assert isinstance(title, str) and title
        self.title = title
        assert isinstance(selector_type, str) and selector_type
        assert selector_type in ["name", "label"]
        self.selector_type = selector_type
        assert isinstance(config_key, str) and config_key
        self.config_key = config_key
        self.intro = markdown_process_name if self.selector_type == "name" else markdown_process_label
        self.skip = markdown_skip_name if self.selector_type == "name" else markdown_skip_label
        self.warning = markdown_warn_name if self.selector_type == "name" else markdown_warn_label

    def _set_next_screen(self, next_screen: str) -> None:
        assert isinstance(next_screen, str)
        self.next_screen = next_screen

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(f"# {self.title}")
        yield Markdown(self.intro)
        yield Markdown(markdown_process_common)
        yield Markdown(self.skip)
        yield Markdown(self.warning)
        yield VerticalScroll(
            ProcessConfig(selector=self.selector_type, hpc=self.parent.PIPE_CONF_HPC),
            id="configs",
        )
        yield Center(Button("Add another process", id="another", variant="success"))
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Skip", id="skip", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    @on(Button.Pressed, "#another")
    def add_config(self) -> None:
        new_config = ProcessConfig(selector=self.selector_type, hpc=self.parent.PIPE_CONF_HPC)
        self.query_one("#configs").mount(new_config)

    @on(Button.Pressed, "#next")
    def save_and_load_next_screen(self) -> None:
        try:
            config_list = []
            for config_widget in self.query("ProcessConfig"):
                tmp_config = {}
                for text_input in config_widget.query("TextInput"):
                    if "hide" in text_input.classes:
                        continue
                    this_input = text_input.query_one(Input)
                    validation_result = this_input.validate(this_input.value)
                    tmp_config[text_input.field_id] = this_input.value
                    if not validation_result.is_valid:
                        text_input.query_one(".validation_msg").update(
                            "\n".join(validation_result.failure_descriptions)
                        )
                    else:
                        text_input.query_one(".validation_msg").update("")
                # Validate the config
                with init_context(self.parent.get_context()):
                    ConfigsCreateConfig(**tmp_config)
                # Add to the config list
                config_list.append(tmp_config)
            # Add to the final config
            new_config = {}
            for tmp_config in config_list:
                process_id_field = f"custom_process_{self.selector_type}_id"
                process_id = tmp_config.get(process_id_field)
                new_config[process_id] = tmp_config
            # Validate and save the new config data
            ConfigsCreateConfig(**{self.config_key: new_config})
            self.parent.TEMPLATE_CONFIG["processes"] = {self.config_key: new_config}
            # Push the next screen
            self.parent.push_screen(self.next_screen)
        except ValueError:
            pass

    @on(Button.Pressed, "#back")
    def on_back_button(self, event: Button.Pressed) -> None:
            """Clear the default config info"""
            self.parent.TEMPLATE_CONFIG.pop("processes", None)

    @on(Button.Pressed, "#skip")
    def skip_to_next_screen(self) -> None:
        self.parent.push_screen(self.next_screen)

    @on(Mount)
    @on(ScreenResume)
    def update_hide_class(self) -> None:
        for config_widget in self.query("ProcessConfig"):
            config_widget.update_hpc_status(self.parent.PIPE_CONF_HPC)


class MultiNamedProcessConfig(MultiProcessConfig):
    def __init__(self) -> None:
        super().__init__(
            title="Configure processes by name", selector_type="name", config_key="named_process_resources"
        )

    @on(Mount)
    @on(ScreenResume)
    def set_next_screen(self) -> None:
        next_screen = "final"
        if self.parent.PIPE_CONF_LABELLED:
            next_screen = "multi_labelled_process_config"
        self._set_next_screen(next_screen)


class MultiLabelledProcessConfig(MultiProcessConfig):
    def __init__(self) -> None:
        super().__init__(
            title="Configure processes by label", selector_type="label", config_key="labelled_process_resources"
        )

    @on(Mount)
    @on(ScreenResume)
    def set_next_screen(self) -> None:
        self._set_next_screen("final")
