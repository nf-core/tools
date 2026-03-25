"""Test Config Create App"""

from nf_core.configs.create import ConfigsCreateApp

INIT_FILE = "../../nf_core/configs/create/__init__.py"


async def test_app_bindings():
    """Test that the app bindings work."""
    app = ConfigsCreateApp()
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


def test_welcome(snap_compare):
    """Test snapshot for the first screen in the app. The welcome screen."""
    assert snap_compare(INIT_FILE, terminal_size=(100, 50))


async def click_lets_go(pilot) -> None:
    await pilot.click("#lets_go")


def test_choose_type(snap_compare):
    """Test snapshot for the choose_type screen.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        screen choose_type
    """

    async def run_before(pilot) -> None:
        await click_lets_go(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


async def click_type_infrastructure(pilot) -> None:
    await click_lets_go(pilot)
    await pilot.click("#type_infrastructure")


def test_choose_infra_type(snap_compare):
    """Test snapshot for the nfcore_question screen
    via the Infrastructure config option.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        screen choose_type
    """

    async def run_before(pilot) -> None:
        await click_type_infrastructure(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


async def click_infra_nfcore(pilot) -> None:
    await click_type_infrastructure(pilot)
    await pilot.click("#type_nfcore")


def test_infra_nfcore_basic_details(snap_compare):
    """Test snapshot for the nf-core basic_details screen
    when configuring an infrastructure config.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press nf-core >
        screen basic_details
    """

    async def run_before(pilot) -> None:
        await click_infra_nfcore(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


async def enter_infra_nfcore_basic_details(pilot) -> None:
    await click_infra_nfcore(pilot)
    await pilot.click("#general_config_name")
    await pilot.press("m", "y", "c", "o", "n", "f", "i", "g")
    await pilot.press("tab")
    await pilot.press("m", "y", " ", "n", "a", "m", "e")
    await pilot.press("tab")
    await pilot.press("@", "m", "y", "h", "a", "n", "d", "l", "e")
    await pilot.press("tab")
    await pilot.press("A", " ", "c", "o", "o", "l", " ", "d", "e", "s", "c", "r", "i", "p", "t", "i", "o", "n")
    await pilot.press("tab")
    await pilot.press("h", "t", "t", "p", "s", ":", "/", "/", "e", "x", "a", "m", "p", "l", "e", ".", "c", "o", "m")


async def submit_infra_nfcore_basic_details(pilot) -> None:
    await enter_infra_nfcore_basic_details(pilot)
    await pilot.click("#next")


def test_entering_infra_nfcore_basic_details(snap_compare):
    """Test snapshot for the entering basic details
    on the nf-core basic_details screen
    when configuring an infrastructure config.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press nf-core >
        screen basic_details
    """

    async def run_before(pilot) -> None:
        await enter_infra_nfcore_basic_details(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_submitting_infra_nfcore_basic_details(snap_compare):
    """Test snapshot for the entering basic details
    on the nf-core basic_details screen
    when configuring an infrastructure config.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press nf-core >
        enter basic details >
        click Next >
        screen hpc_question
    """

    async def run_before(pilot) -> None:
        await submit_infra_nfcore_basic_details(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


async def enter_infra_nfcore_hpc_details(pilot) -> None:
    await submit_infra_nfcore_basic_details(pilot)
    await pilot.click("#type_hpc")
    await pilot.click("#scheduler")
    await pilot.press("p", "b", "s", "p", "r", "o")
    await pilot.press("tab")
    await pilot.press("m", "y", "q", "u", "e", "u", "e")
    await pilot.press("tab")
    await pilot.press("0", ".", "7", "5")


async def submit_infra_nfcore_hpc_details(pilot) -> None:
    await enter_infra_nfcore_hpc_details(pilot)
    await pilot.click("#toconfiguration")


def test_entering_infra_nfcore_hpc_details(snap_compare):
    """Test snapshot for entering HPC details
    when configuring an infrastructure config
    for use with nf-core.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press nf-core >
        enter basic details >
        click Next >
        click HPC >
        enter HPC details
    """

    async def run_before(pilot) -> None:
        await enter_infra_nfcore_hpc_details(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_submitting_infra_nfcore_hpc_details(snap_compare):
    """Test snapshot for entering HPC details
    when configuring an infrastructure config
    for use with nf-core.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press nf-core >
        enter basic details >
        click Next >
        click HPC >
        enter HPC details >
        click Continue >
        screen final_infra_details
    """

    async def run_before(pilot) -> None:
        await submit_infra_nfcore_hpc_details(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_infra_custom_basic_details(snap_compare):
    """Test snapshot for the custom pipeline basic_details screen
    when configuring an infrastructure config.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Infrastructure config >
        press Custom >
        screen basic_details
    """

    async def run_before(pilot) -> None:
        await pilot.click("#lets_go")
        await pilot.click("#type_infrastructure")
        await pilot.click("#type_custom")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


def test_choose_pipe_type(snap_compare):
    """Test snapshot for the nfcore_question screen
    via the Pipeline config option.
    Steps to get to this screen:
        screen welcome > press Let's go! >
        press Pipeline config >
        screen choose_type
    """

    async def run_before(pilot) -> None:
        await pilot.click("#lets_go")
        await pilot.click("#type_pipeline")

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)
