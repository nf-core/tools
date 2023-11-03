import logging
import os
from textwrap import dedent

import git
from github import Github, GithubException
from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.pipelines.create.utils import TextInput

log = logging.getLogger(__name__)

github_text_markdown = """
# Create a GitHub repo

After creating the pipeline template locally, we can create a GitHub repository and push the code to it.
"""
repo_config_markdown = """
Please select the the GitHub repository settings:
"""
exit_help_text_markdown = f"""
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


class GithubRepo(Screen):
    """Create a GitHub repository and push all branches."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Horizontal():
            with VerticalScroll():
                yield Markdown(dedent(github_text_markdown))
                with Horizontal():
                    yield TextInput(
                        "gh_username",
                        "GitHub username",
                        "Your GitHub username",
                        classes="column",
                    )
                    token = "GITHUB_AUTH_TOKEN" in os.environ
                    yield TextInput(
                        "token",
                        "GitHub token",
                        "Your GitHub personal access token for login. Will use the environment variable GITHUB_AUTH_TOKEN if set.",
                        classes="column",
                        disabled=token,
                    )
                yield Markdown(dedent(repo_config_markdown))
                with Horizontal():
                    yield Switch(value=False, id="private")
                    yield Static("Select if the new GitHub repo must be private.", classes="custom_grid")
                with Horizontal():
                    yield Switch(value=True, id="push")
                    yield Static(
                        "Select if you would like to push all the pipeline template files to your GitHub repo\nand all the branches required to keep the pipeline up to date with new releases of nf-core.",
                        classes="custom_grid",
                    )
                yield Center(
                    Button("Create GitHub repo", id="create", variant="success"),
                    Button("Finish without creating a repo", id="exit", variant="primary"),
                    classes="cta",
                )
            yield Center(self.parent.LOG_HANDLER.console, classes="cta log")

    @on(Button.Pressed, "#create")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Create a GitHub repo"""
        # Save GitHub username and token
        github_variables = {}
        for text_input in self.query("TextInput"):
            this_input = text_input.query_one(Input)
            github_variables[text_input.field_id] = this_input.value
        # Save GitHub repo config
        for switch_input in self.query("Switch"):
            this_switch = switch_input.query_one(Switch)
            github_variables[switch_input.field_id] = this_switch.value

        # Pipeline git repo
        pipeline_repo = git.Repo.init(self.parent.TEMPLATE_CONFIG.outdir)

        # GitHub authentication
        if "GITHUB_AUTH_TOKEN" in os.environ:
            github_auth = self._github_authentication(github_variables["gh_username"], os.environ["GITHUB_AUTH_TOKEN"])
        elif github_variables["token"]:
            github_auth = self._github_authentication(github_variables["gh_username"], github_variables["token"])
        else:
            raise UserWarning(
                f"Could not authenticate to GitHub with user name '{github_variables['gh_username']}'."
                "Please provide an authentication token or set the environment variable 'GITHUB_AUTH_TOKEN'."
                f"\n{exit_help_text_markdown}"
            )

        user = github_auth.get_user()
        org = None
        # Make sure that the authentication was successful
        try:
            user.login
        except GithubException.GithubException as e:
            raise UserWarning(
                f"Could not authenticate to GitHub with user name '{github_variables['gh_username']}'."
                "Please make sure that the provided user name and token are correct."
                f"\n{exit_help_text_markdown}"
            )

        # Check if organisation exists
        # If the organisation is nf-core or it doesn¡t exist, the repo will be created in the user account
        if self.parent.TEMPLATE_CONFIG.org != "nf-core":
            try:
                org = github_auth.get_organization(self.parent.TEMPLATE_CONFIG.org)
            except GithubException.UnknownObjectException:
                pass

        # Create the repo
        try:
            if org:
                self._create_repo_and_push(org, pipeline_repo, github_variables["private"], github_variables["push"])
            else:
                # Create the repo in the user's account
                self._create_repo_and_push(user, pipeline_repo, github_variables["private"], github_variables["push"])
        except UserWarning as e:
            log.info(f"There was an error with message: {e}" f"\n{exit_help_text_markdown}")

        self.parent.switch_screen("bye")

    @on(Button.Pressed, "#exit")
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Show help message and exit"""
        log.info(exit_help_text_markdown)
        self.parent.switch_screen("bye")

    def _create_repo_and_push(self, org, pipeline_repo, private, push):
        """Create a GitHub repository and push all branches."""
        # Check if repo already exists
        try:
            repo = org.get_repo(self.parent.TEMPLATE_CONFIG.name)
            # Check if it has a commit history
            try:
                repo.get_commits().totalCount
                raise UserWarning(f"GitHub repository '{self.parent.TEMPLATE_CONFIG.name}' already exists")
            except GithubException.GithubException:
                # Repo is empty
                repo_exists = True
        except GithubException.UnknownObjectException:
            # Repo doesn't exist
            repo_exists = False

        # Create the repo
        if not repo_exists:
            repo = org.create_repo(
                self.parent.TEMPLATE_CONFIG.name, description=self.parent.TEMPLATE_CONFIG.description, private=private
            )

        # Add the remote and push
        pipeline_repo.create_remote("origin", repo.clone_url)
        if push:
            pipeline_repo.remotes.origin.push(all=True).raise_if_error()

    def _github_authentication(self, gh_username, gh_token):
        """Authenticate to GitHub"""
        log.debug(f"Authenticating GitHub as {gh_username}")
        github_auth = Github(gh_username, gh_token)
        return github_auth
