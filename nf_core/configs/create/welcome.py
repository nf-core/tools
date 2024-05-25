from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from nf_core.utils import nfcore_logo

markdown = """
# Welcome to the nf-core config creation wizard

This app will help you create **Nextflow configuration files**
for both **infrastructure** and **pipeline-specific** configs.

## Config Types

- **Infrastructure configs** allow you to define the computational environment you
will run the pipelines on (memory, CPUs, scheduling system, container engine
etc.).
- **Pipeline configs** allow you to tweak resources of a particular step of a
pipeline. For example process X should request 8.GB of memory.

## Using Configs

The resulting config file can be used with a pipeline with `-c <filename>.conf`.

They can also be added to the centralised
[nf-core/configs](https://github.com/nf-core/configs) repository, where they
can be used by anyone running nf-core pipelines on your infrastructure directly
using `-profile <configname>`.
"""


class WelcomeScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(
            "\n" + "\n".join(nfcore_logo) + "\n",
            id="logo",
        )
        yield Markdown(markdown)
        yield Center(Button("Let's go!", id="start", variant="success"), classes="cta")
