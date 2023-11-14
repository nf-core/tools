""" Test Pipeline Create App """
import pytest

from nf_core.pipelines.create import PipelineCreateApp


@pytest.mark.asyncio
async def test_app_bindings():
    """Test that the app bindings work."""
    app = PipelineCreateApp()
    async with app.run_test() as pilot:
        # Test pressing the D key
        assert app.dark == True
        await pilot.press("d")
        assert app.dark == False
        await pilot.press("d")
        assert app.dark == True

        # Test pressing the Q key
        await pilot.press("q")
        assert app.return_code == 0


def test_welcome(snap_compare):
    """Test snapshot for the first screen in the app. The welcome screen."""
    assert snap_compare("../nf_core/pipelines/create/__init__.py")


def test_choose_type(snap_compare):
    """Test snapshot for the choose_type screen.
    screen welcome > press start > screen choose_type
    """

    async def run_before(pilot) -> None:
        await pilot.click("#start")

    assert snap_compare("../nf_core/pipelines/create/__init__.py", terminal_size=(100, 50), run_before=run_before)
