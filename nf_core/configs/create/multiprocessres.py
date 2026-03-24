"""Get information about which process/label the user wants to configure."""

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, HorizontalGroup, Vertical, VerticalScroll
from textual.events import Mount, ScreenResume
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Markdown, Static, Switch

from nf_core.configs.create.utils import ConfigsCreateConfig, TextInput, init_context


class ProcessConfig(HorizontalGroup):
    """Get resource requirements for a single process."""

    def __init__(self, selector: str, hpc: bool) -> None:
        super().__init__()
        assert selector in ["name", "label"]
        self.selector = selector
        self.hpc = hpc
        self.use_local_exec = False

    def compose(self) -> ComposeResult:
        yield TextInput(
            "custom_process_id",
            "",
            f"Process {self.selector}:",
            "",
            classes="column",
        )
        yield TextInput(
            "custom_process_ncpus",
            "2",
            "# CPUs:",
            "2",
            classes="column",
        )
        yield TextInput(
            "custom_process_memgb",
            "8",
            "Memory (GB):",
            "8",
            classes="column",
        )
        yield TextInput(
            "custom_process_hours",
            "1",
            "Walltime (hours):",
            "1",
            classes="column",
        )
        yield TextInput(
            "custom_process_queue",
            "queue name",
            "HPC queue:",
            "",
            classes=("column" + (" hide" if not self.hpc else "")),
        )
        with Vertical(
            classes=("labelled-toggle column" + (" hide" if not self.hpc else "")), id="toggle_use_local_exec_group"
        ):
            yield Label("Use local executor?", id="toggle_use_local_exec_label", classes="field_help")
            with Horizontal(classes="labelled-toggle"):
                yield Switch(id="toggle_use_local_exec", value=self.use_local_exec)
                yield Label(
                    "Yes" if self.use_local_exec else "No",
                    id="toggle_use_local_exec_state_label",
                    classes="toggle_use_local_exec_state_label",
                )
            yield Static(classes="labelled-toggle-filler")  # Filler
        with Vertical(classes="labelled-toggle"):
            yield Label("Remove", id="remove-process-config", classes="field_help")
            yield Button("-", id="remove", variant="error", classes="remove-process-button")
            yield Static(classes="labelled-toggle-filler")  # Filler

    @on(Switch.Changed, "#toggle_use_local_exec")
    def on_toggle_switch(self, event: Switch.Changed) -> None:
        """Handle toggling the local executor switch"""

        self.use_local_exec = event.value

        # Update the switch label
        for label in self.query(Label):
            if label.id == f"{event.switch.id}_state_label":
                label.update("Yes" if event.value else "No")

    @on(Button.Pressed, "#remove")
    def remove_widget(self) -> None:
        self.remove()

    def update_hpc_status(self, hpc: bool) -> None:
        self.hpc = hpc
        for id in ["custom_process_queue", "toggle_use_local_exec_group"]:
            if self.hpc:
                self.get_widget_by_id(id).remove_class("hide")
            else:
                self.get_widget_by_id(id).add_class("hide")


class MultiProcessConfig(Screen):
    """Get resource requirements for multiple processes."""

    def __init__(self, selector_type: str, config_key: str, title: str) -> None:
        super().__init__()
        assert isinstance(title, str) and title
        self.title = title
        assert isinstance(selector_type, str) and selector_type
        self.selector_type = selector_type
        assert isinstance(config_key, str) and config_key
        self.config_key = config_key

    def _set_next_screen(self, next_screen: str) -> None:
        assert isinstance(next_screen, str)
        self.next_screen = next_screen

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(f"# {self.title}")
        yield VerticalScroll(
            ProcessConfig(selector=self.selector_type, hpc=self.parent.PIPE_CONF_HPC),
            ProcessConfig(selector=self.selector_type, hpc=self.parent.PIPE_CONF_HPC),
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
        new_config = ProcessConfig(selector="name", hpc=self.parent.PIPE_CONF_HPC)
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
                if self.parent.PIPE_CONF_HPC:
                    local_exec_switch = config_widget.query_one("#toggle_use_local_exec")
                    if local_exec_switch.value:
                        tmp_config['executor'] = "local"
                # Validate the config
                with init_context(self.parent.get_context()):
                    ConfigsCreateConfig(**tmp_config)
                # Add to the config list
                config_list.append(tmp_config)
            # Add to the final config
            new_config = {self.config_key: {}}
            for tmp_config in config_list:
                process_id = tmp_config.get("custom_process_id")
                new_config[self.config_key][process_id] = tmp_config
            self.parent.TEMPLATE_CONFIG = self.parent.TEMPLATE_CONFIG.model_copy(update=new_config)
            # Push the next screen
            self.parent.push_screen(self.next_screen)
        except ValueError:
            pass

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
            title='Configure processes by label', selector_type='label', config_key='labelled_process_resources'
        )

    @on(Mount)
    @on(ScreenResume)
    def set_next_screen(self) -> None:
        self._set_next_screen("final")