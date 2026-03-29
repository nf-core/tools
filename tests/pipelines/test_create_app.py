"""Test Pipeline Create App"""

from unittest import mock

from textual.widgets import Button, Input

from nf_core.pipelines.create import PipelineCreateApp
from nf_core.pipelines.create import utils as create_utils
from nf_core.pipelines.create.utils import TextInput

INIT_FILE = "../../nf_core/pipelines/create/__init__.py"


async def press_screen_button(pilot, button_id: str) -> None:
    """Press a button without relying on it being inside the visible viewport."""
    pilot.app.screen.query_one(button_id, Button).press()
    await pilot.pause()


async def test_app_bindings():
    """Test that the app bindings work."""
    app = PipelineCreateApp()
    async with app.run_test() as pilot:
        # Test pressing the D key
        assert app.theme == "textual-dark"
        await pilot.press("d")
        assert app.theme == "textual-light"
        await pilot.press("d")
        assert app.theme == "textual-dark"

        # Test pressing the Q key
        await pilot.press("q")
        assert app.return_code == 0


async def test_custom_org_metadata_stays_empty_until_blur():
    """Empty org metadata fields should only be restored after the input loses focus."""
    app = PipelineCreateApp()

    async with app.run_test() as pilot:
        pilot.app.NFCORE_PIPELINE = False
        create_utils.NFCORE_PIPELINE_GLOBAL = False
        pilot.app.push_screen("basic_details")
        await pilot.pause()

        screen = pilot.app.screen
        org_input = screen.query_one("#org", TextInput).query_one(Input)
        org_name_input = screen.query_one("#org_name", TextInput).query_one(Input)
        org_url_input = screen.query_one("#org_url", TextInput).query_one(Input)

        org_input.focus()
        await pilot.pause()
        await pilot.press("t", "e", "s", "t", "p", "r", "e", "f", "i", "x")
        assert org_input.value == "testprefix"
        assert org_name_input.value == "testprefix"
        assert org_url_input.value == "https://github.com/testprefix"

        org_name_input.focus()
        await pilot.pause()
        await pilot.press("backspace")
        assert org_name_input.value == ""

        org_url_input.focus()
        await pilot.pause()
        assert org_name_input.value == "testprefix"

        await pilot.press("backspace")
        assert org_url_input.value == ""

        screen.query_one("#name", TextInput).query_one(Input).focus()
        await pilot.pause()
        assert org_url_input.value == "https://github.com/testprefix"


def test_welcome(snap_compare):
    """Test snapshot for the first screen in the app. The welcome screen."""
    assert snap_compare(INIT_FILE, terminal_size=(100, 50))


def test_choose_type(snap_compare):
    """Test snapshot for the choose_type screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_basic_details_nfcore(snap_compare):
    """Test snapshot for the basic_details screen of an nf-core pipeline.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_basic_details_custom(snap_compare):
    """Test snapshot for the basic_details screen of a custom pipeline.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press custom >
        screen basic_details
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_custom")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_type_nfcore(snap_compare):
    """Test snapshot for the type_nfcore screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_nfcore
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#name")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await press_screen_button(pilot, "#next")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_type_nfcore_validation(snap_compare):
    """Test snapshot for the type_nfcore screen.
    Validation errors should appear when input fields are empty.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > press next >
        ERRORS
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#next")
        await pilot.pause(delay=1)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_type_custom(snap_compare):
    """Test snapshot for the type_custom screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press custom >
        screen basic_details > enter pipeline details > press next >
        screen type_custom
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_custom")
        await pilot.click("#name")
        await pilot.press("tab")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await press_screen_button(pilot, "#next")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_final_details(snap_compare):
    """Test snapshot for the final_details screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_nfcore > press continue >
        screen final_details
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#name")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await pilot.click("#next")
        await pilot.click("#continue")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_customisation_help(snap_compare):
    """Test snapshot for the type_custom screen - showing help messages.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_custom > press Show more
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_custom")
        await pilot.click("#name")
        await pilot.press("tab")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await press_screen_button(pilot, "#next")
        await pilot.pause(delay=1)
        await press_screen_button(pilot, "#show_help_github_badges")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_github_question(tmp_path, snap_compare):
    """Test snapshot for the github_repo_question screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_nfcore > press continue >
        screen final_details > press finish > close logging screen >
        screen github_repo_question
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#name")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await pilot.click("#next")
        await pilot.click("#continue")
        await pilot.press("backspace")
        await pilot.press("tab")
        await pilot.press(*str(tmp_path))
        await pilot.click("#finish")
        await pilot.app.workers.wait_for_complete()
        await pilot.click("#close_screen")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


@mock.patch("nf_core.pipelines.create.githubrepo.GithubRepo._get_github_credentials")
def test_github_details(mock_get_github_credentials, tmp_path, snap_compare):
    """Test snapshot for the github_repo screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_nfcore > press continue >
        screen final_details > press finish > close logging screen >
        screen github_repo_question > press create repo >
        screen github_repo
    """

    async def run_before(pilot) -> None:
        mock_get_github_credentials.return_value = (
            None,
            None,
        )  # mock the github credentials to have consistent snapshots
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#name")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await pilot.click("#next")
        await pilot.click("#continue")
        await pilot.press("backspace")
        await pilot.press("tab")
        await pilot.press(*str(tmp_path))
        await pilot.click("#finish")
        await pilot.app.workers.wait_for_complete()
        await pilot.click("#close_screen")
        await pilot.click("#github_repo")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_github_exit_message(tmp_path, snap_compare):
    """Test snapshot for the github_exit screen.
    Steps to get to this screen:
        screen welcome > press start >
        screen choose_type > press nf-core >
        screen basic_details > enter pipeline details > press next >
        screen type_nfcore > press continue >
        screen final_details > press finish > close logging screen >
        screen github_repo_question > press create repo >
        screen github_repo > press exit (close without creating a repo) >
        screen github_exit
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")
        await pilot.click("#type_nfcore")
        await pilot.click("#name")
        await pilot.press("m", "y", "p", "i", "p", "e", "l", "i", "n", "e")
        await pilot.press("tab")
        await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
        await pilot.press("tab")
        await pilot.press("M", "e")
        await pilot.click("#next")
        await pilot.click("#continue")
        await pilot.press("backspace")
        await pilot.press("tab")
        await pilot.press(*str(tmp_path))
        await pilot.click("#finish")
        await pilot.app.workers.wait_for_complete()
        await pilot.click("#close_screen")
        await pilot.click("#github_repo")
        await pilot.click("#exit")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)
