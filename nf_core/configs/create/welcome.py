"""Intro information to help inform user what we are about to do"""

from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

from nf_core.utils import nfcore_logo

markdown = """
# Welcome to the nf-core config creation wizard

This app will help you create **Nextflow configuration files**
for both:

- **Infrastructure** configs for defining computing environment for all
  pipelines, and
- **Pipeline** configs for defining pipeline-specific resource requirements

## Using Configs

The resulting config file can be used with a pipeline with adding `-c
<filename>.conf` to a `nextflow run` command.

They can also be added to the centralised
[nf-core/configs](https://github.com/nf-core/configs) repository, where they
can be used directly by anyone running nf-core pipelines on your infrastructure
specifying `nextflow run -profile <configname>`.
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
        yield Center(Button("Let's go!", id="lets_go", variant="success"), classes="cta")
