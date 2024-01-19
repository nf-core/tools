from textual.app import ComposeResult
from textual.containers import Center
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Markdown, Static

exit_help_text_markdown = """
If you would like to create the GitHub repository later, you can do it manually by following these steps:

1. Create a new GitHub repository
2. Add the remote to your local repository
```bash
cd <pipeline_directory>
git remote add origin git@github.com:<username>/<repo_name>.git
```
3. Push the code to the remote
```bash
git push --all origin
```
"""


class GithubExit(Screen):
    """A screen to show a help text when a GitHub repo is NOT created."""

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
        yield Markdown(exit_help_text_markdown)
        yield Center(
            Button("Close App", id="close_app", variant="success"),
            Button("Show Logging", id="show_logging", variant="primary"),
            classes="cta",
        )
