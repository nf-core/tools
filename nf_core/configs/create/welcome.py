from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

markdown = """
This app will help you create a new nextflow configuration file.

It allows you to create both nextflow configs for both infrastructure and pipelines.

Infrastructure configs are used to define the computational environment in which nf-core pipelines are run, e.g.  what memory or CPUs are available, if there is a scheduler, which container engine to use.
Pipeline configs are used to tweak the resources of different steps of a particular pipeline to suit your data, e.g. step X should request only 8.GB of memory.

While both types of configs can be used in your own pipeline runs (passing the file to Nextflow with `-c`), they can also be added to the centralised [nf-core/configs](https://github.com/nf-core/configs) repository, where they can be used by anyone running nf-core pipelines directly with `-profile`.
"""


class WelcomeScreen(Screen):
    """A welcome screen for the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Create a nextflow config
                """
            )
        )
        yield Static(
            f"\n[green]{' ' * 40},--.[grey39]/[green],-."
            + "\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
            + "\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
            + "\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
            + "\n[green]                                       `._,._,'\n",
            id="logo",
        )
        yield Markdown(markdown)
        yield Center(Button("Let's go!", id="start", variant="success"), classes="cta")
