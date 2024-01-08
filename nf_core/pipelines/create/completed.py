from textwrap import dedent

from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static


class Completed(Screen):
    """A screen to show the final text and exit the app."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(
            f"\n[green]{' ' * 40},--.[grey39]/[green],-."
            + "\n[blue]        ___     __   __   __   ___     [green]/,-._.--~\\"
            + "\n[blue]|\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {"
            + "\n[blue]   | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,"
            + "\n[green]                                       `._,._,'\n",
            id="logo",
        )

        completed_text_markdown = f"""
        - A pipeline has been created at '`{self.parent.TEMPLATE_CONFIG.outdir + "/" + self.parent.TEMPLATE_CONFIG.org + "-" + self.parent.TEMPLATE_CONFIG.name}`'.
        - A GitHub repository '`{self.parent.TEMPLATE_CONFIG.name}`' has been created in the {"user's" if self.parent.TEMPLATE_CONFIG.org == "nf-core" else ""} GitHub organisation account{ " `" + self.parent.TEMPLATE_CONFIG.org + "`" if self.parent.TEMPLATE_CONFIG.org != "nf-core" else ""}.

        !!!!!! IMPORTANT !!!!!!

        If you are interested in adding your pipeline to the nf-core community,
        PLEASE COME AND TALK TO US IN THE NF-CORE SLACK BEFORE WRITING ANY CODE!

        - Please read: [https://nf-co.re/developers/adding_pipelines#join-the-community](https://nf-co.re/developers/adding_pipelines#join-the-community)
        """

        yield Markdown(dedent(completed_text_markdown))
        yield Center(
            Button("Close App", id="close_app", variant="success"),
            classes="cta",
        )
