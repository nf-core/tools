"""Run config auto generator"""
import logging
import re
from pathlib import Path
from textwrap import dedent

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Markdown, Switch

# from nf_core.configs.create.utils import (
#     ConfigsCreateConfig,
#     TextInput,
#     init_context
# )

config_exists_warn = """
> ⚠️  **The config file you are trying to create already exists.**
>
> If you continue, you will **overwrite** the existing config.
> Please change the config name to create a different config!.
"""

class AutoProcesses(Screen):
    """Name, description, author, etc."""

    def __init__(self) -> None:
        super().__init__()
        self.auto_load_all = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Auto-load your pipeline's process
                The processes from your pipeline will be loaded based on your previous config 
                pipeline path.
                """
            )
        )
        yield Horizontal(
            Label("Auto-load all processes from pipeline path?", id="toggle_auto_load_all_label", classes="feature_title"),
            Switch(id="toggle_auto_load_all", value=self.auto_load_all),
            Label(
                "Yes" if self.auto_load_all else "No",
                id="toggle_auto_load_all_state_label"
            ),
            classes="custom_grid",
        )

        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Next", id="next", variant="success"),
            classes="cta",
        )

    def on_mount(self) -> None:
        pipeline_path = self.parent.TEMPLATE_CONFIG.config_pipeline_path
        process_map = self.scan_nextflow_files(pipeline_path)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        logging.info(process_map)

    def scan_nextflow_files(self, pipeline_path: str):
        process_map = {}
        for nf_file in Path(pipeline_path).rglob("*.nf"):
            content = nf_file.read_text()
            for match in re.finditer(r'process\s+(\w+)\s*\{([^}]*)\}', content, re.DOTALL):
                process_name = match.group(1)
                process_code = match.group(2)

                process_code = re.sub(r'//.*', '', process_code)
                
                labels = re.findall(r'label\s+[\'"](\w+)[\'"]', process_code)
                process_map[process_name] = labels if labels else []
        
        return process_map
    
    @on(Switch.Changed)
    def on_toggle_switch(self, event: Switch.Changed) -> None:
        """ Handle toggling the switches that determine whether to auto-load """
        valid_toggles = {
            'toggle_auto_load_all': 'auto_load_all',
        }

        if event.switch.id not in valid_toggles:
            return

        attr = valid_toggles[event.switch.id]
        self.__setattr__(attr, event.value)

        # Update the switch label
        for label in self.query(Label):
            if label.id == f'{event.switch.id}_state_label':
                label.update("Yes" if event.value else "No")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "next" and not self.auto_load_all:
            self.app.push_screen("pipeline_config_question")
        elif event.button.id == "next" and self.auto_load_all:
            self.app.push_screen("auto_process_question")