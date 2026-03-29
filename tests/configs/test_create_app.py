"""Test Config Create App"""

from pathlib import Path
from tempfile import TemporaryDirectory

from nf_core.configs.create import ConfigsCreateApp
from nf_core.configs.create.utils import SUPPORTED_CONTAINERS

from ..test_configs import INFRA_SINGULARITY_CONFIG

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
    await pilot.press(*list("myconfig"))
    await pilot.press("tab")
    await pilot.press(*list("my name"))
    await pilot.press("tab")
    await pilot.press(*list("@myhandle"))
    await pilot.press("tab")
    await pilot.press(*list("A cool description"))
    await pilot.press("tab")
    await pilot.press(*list("https://example.com"))


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
    await pilot.press(*list("pbspro"))
    await pilot.press("tab")
    await pilot.press(*list("myqueue"))
    await pilot.press("tab")
    await pilot.press(*list("0.75"))


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


def enter_infra_final_details(container):
    assert container in SUPPORTED_CONTAINERS

    async def _enter_infra_final_details(pilot) -> None:
        await submit_infra_nfcore_hpc_details(pilot)
        await pilot.click("#container_system")
        for container_system in SUPPORTED_CONTAINERS:
            if container_system == container:
                break
            await pilot.press("down")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press(*list("128"))
        await pilot.press("tab")
        await pilot.press(*list("48"))
        await pilot.press("tab")
        await pilot.press(*list("9.5"))
        await pilot.press("tab")
        await pilot.press(*list("200"))
        await pilot.press("tab")
        await pilot.press(*list("0.25"))
        await pilot.press("tab")
        await pilot.press(*list("25"))
        await pilot.press("tab")
        if container in ["singularity", "charliecloud"]:
            await pilot.press(*list(f"/{container}/cachedir"))
        await pilot.press("tab")
        await pilot.press(*list("/data/igenomes/cache"))
        await pilot.press("tab")
        await pilot.press(*list("/tmp/scratch"))
        await pilot.press("tab")
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press(*list("2"))

    return _enter_infra_final_details


def submit_infra_final_details(container):
    async def _submit_infra_final_details(pilot) -> None:
        await enter_infra_final_details(container)(pilot)
        await pilot.click("#finish")

    return _submit_infra_final_details


def write_infra_details(container, outdir="."):
    assert isinstance(outdir, str)
    assert Path(outdir).is_dir()

    async def _write_infra_details(pilot) -> None:
        await submit_infra_final_details(container)(pilot)
        await pilot.click("#savelocation")
        await pilot.press(*list(outdir))
        await pilot.click("#close_app")

    return _write_infra_details


def test_entering_infra_final_details_docker(snap_compare):
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
        await enter_infra_final_details("docker")(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 100), run_before=run_before)


def test_entering_infra_final_details_singularity(snap_compare):
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
        await enter_infra_final_details("singularity")(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 100), run_before=run_before)


def test_submitting_infra_final_details_singularity(snap_compare):
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
        click Finish >
        screen final
    """

    async def run_before(pilot) -> None:
        await submit_infra_final_details("singularity")(pilot)

    assert snap_compare(INIT_FILE, terminal_size=(100, 50), run_before=run_before)


async def test_writing_infra_details_singularity():
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
        click Finish >
        click Save and close!
    """

    app = ConfigsCreateApp()
    async with app.run_test(size=(100, 50)) as pilot:
        # Make a temporary directory to store the output
        tmpdir = TemporaryDirectory()

        await write_infra_details("singularity", outdir=tmpdir.name)(pilot)

        config_file = Path(tmpdir.name) / "myconfig.conf"
        with open(config_file) as f:
            config = f.read()
        assert config == INFRA_SINGULARITY_CONFIG
        tmpdir.cleanup()


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
