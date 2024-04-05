import logging
import os
from pathlib import Path
from textwrap import dedent

import git
import yaml
from github import Github, GithubException, UnknownObjectException
from textual import work
from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Markdown, Static, Switch

from nf_core.pipelines.create.loggingscreen import LoggingScreen
from nf_core.pipelines.create.utils import ShowLogs, TextInput

log = logging.getLogger(__name__)

github_text_markdown = """
Now that we have created a new pipeline locally, we can create a new
GitHub repository using the GitHub API and push the code to it.
"""


class GithubRepo(Screen):
    """Create a GitHub repository and push all branches."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Markdown(
            dedent(
                """
                # Create GitHub repository
                """
            )
        )
        yield Markdown(dedent(github_text_markdown))
        with Horizontal(classes="ghrepo-cols"):
            gh_user, gh_token = self._get_github_credentials()
            yield TextInput(
                "gh_username",
                "GitHub username",
                "Your GitHub username",
                default=gh_user[0] if gh_user is not None else "GitHub username",
                classes="column",
            )
            yield TextInput(
                "token",
                "GitHub token",
                "Your GitHub [link=https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens]personal access token[/link] for login.",
                default=gh_token if gh_token is not None else "GitHub token",
                password=True,
                classes="column",
            )
            yield Button("Show", id="show_password")
            yield Button("Hide", id="hide_password")
        with Horizontal(classes="ghrepo-cols"):
            yield TextInput(
                "repo_name",
                "Repository name",
                "The name of the new GitHub repository",
                default=self.parent.TEMPLATE_CONFIG.name,
                classes="column",
            )
        with Horizontal(classes="ghrepo-cols"):
            yield Switch(value=False, id="private")
            with Vertical():
                yield Static("Private", classes="")
                yield Static("Select to make the new GitHub repo private.", classes="feature_subtitle")
        with Horizontal(classes="ghrepo-cols"):
            yield Switch(value=True, id="push")
            with Vertical():
                yield Static("Push files", classes="custom_grid")
                yield Static(
                    "Select to push pipeline files and branches to your GitHub repo.",
                    classes="feature_subtitle",
                )
        yield Center(
            Button("Back", id="back", variant="default"),
            Button("Create GitHub repo", id="create_github", variant="success"),
            Button("Finish without creating a repo", id="exit", variant="primary"),
            classes="cta",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Create a GitHub repo or show help message and exit"""
        if event.button.id == "show_password":
            self.add_class("displayed")
            text_input = self.query_one("#token", TextInput)
            text_input.query_one(Input).password = False
        elif event.button.id == "hide_password":
            self.remove_class("displayed")
            text_input = self.query_one("#token", TextInput)
            text_input.query_one(Input).password = True
        elif event.button.id == "create_github":
            # Create a GitHub repo

            # Save GitHub username, token and repo name
            github_variables = {}
            for text_input in self.query("TextInput"):
                this_input = text_input.query_one(Input)
                github_variables[text_input.field_id] = this_input.value
            # Save GitHub repo config
            for switch_input in self.query("Switch"):
                github_variables[switch_input.id] = switch_input.value

            # Pipeline git repo
            pipeline_repo = git.Repo.init(
                Path(self.parent.TEMPLATE_CONFIG.outdir)
                / Path(self.parent.TEMPLATE_CONFIG.org + "-" + github_variables["repo_name"])
            )

            # GitHub authentication
            if github_variables["token"]:
                github_auth = self._github_authentication(github_variables["gh_username"], github_variables["token"])
            else:
                raise UserWarning(
                    f"Could not authenticate to GitHub with user name '{github_variables['gh_username']}'."
                    "Please provide an authentication token or set the environment variable 'GITHUB_AUTH_TOKEN'."
                )

            user = github_auth.get_user()
            org = None
            # Make sure that the authentication was successful
            try:
                user.login
                log.debug("GitHub authentication successful")
            except GithubException:
                raise UserWarning(
                    f"Could not authenticate to GitHub with user name '{github_variables['gh_username']}'."
                    "Please make sure that the provided user name and token are correct."
                )

            # Check if organisation exists
            # If the organisation is nf-core or it doesn't exist, the repo will be created in the user account
            if self.parent.TEMPLATE_CONFIG.org != "nf-core":
                try:
                    org = github_auth.get_organization(self.parent.TEMPLATE_CONFIG.org)
                    log.info(
                        f"Repo will be created in the GitHub organisation account '{self.parent.TEMPLATE_CONFIG.org}'"
                    )
                except UnknownObjectException:
                    pass

            # Create the repo
            try:
                if org:
                    self._create_repo_and_push(
                        org,
                        github_variables["repo_name"],
                        pipeline_repo,
                        github_variables["private"],
                        github_variables["push"],
                    )
                else:
                    # Create the repo in the user's account
                    log.info(
                        f"Repo will be created in the GitHub organisation account '{github_variables['gh_username']}'"
                    )
                    self._create_repo_and_push(
                        user,
                        github_variables["repo_name"],
                        pipeline_repo,
                        github_variables["private"],
                        github_variables["push"],
                    )
            except UserWarning as e:
                log.info(f"There was an error with message: {e}")
                self.parent.switch_screen("github_exit")

            self.parent.LOGGING_STATE = "repo created"
            self.parent.switch_screen(LoggingScreen())

    @work(thread=True, exclusive=True)
    def _create_repo_and_push(self, org, repo_name, pipeline_repo, private, push):
        """Create a GitHub repository and push all branches."""
        self.post_message(ShowLogs())
        # Check if repo already exists
        try:
            repo = org.get_repo(repo_name)
            # Check if it has a commit history
            try:
                repo.get_commits().totalCount
                raise UserWarning(f"GitHub repository '{repo_name}' already exists")
            except GithubException:
                # Repo is empty
                repo_exists = True
            except UserWarning as e:
                # Repo already exists
                log.error(e)
                return
        except UnknownObjectException:
            # Repo doesn't exist
            repo_exists = False

        # Create the repo
        if not repo_exists:
            repo = org.create_repo(repo_name, description=self.parent.TEMPLATE_CONFIG.description, private=private)
            log.info(f"GitHub repository '{repo_name}' created successfully")

        # Add the remote and push
        try:
            pipeline_repo.create_remote("origin", repo.clone_url)
        except git.exc.GitCommandError:
            # Remote already exists
            pass
        if push:
            pipeline_repo.remotes.origin.push(all=True).raise_if_error()

    def _github_authentication(self, gh_username, gh_token):
        """Authenticate to GitHub"""
        log.debug(f"Authenticating GitHub as {gh_username}")
        github_auth = Github(gh_username, gh_token)
        return github_auth

    def _get_github_credentials(self):
        """Get GitHub credentials"""
        gh_user = None
        gh_token = None
        # Use gh CLI config if installed
        gh_cli_config_fn = os.path.expanduser("~/.config/gh/hosts.yml")
        if os.path.exists(gh_cli_config_fn):
            with open(gh_cli_config_fn) as fh:
                gh_cli_config = yaml.safe_load(fh)
                gh_user = (gh_cli_config["github.com"]["user"],)
                gh_token = gh_cli_config["github.com"]["oauth_token"]
        # If gh CLI not installed, try to get credentials from environment variables
        elif os.environ.get("GITHUB_TOKEN") is not None:
            gh_token = self.auth = os.environ["GITHUB_TOKEN"]
        return (gh_user, gh_token)
