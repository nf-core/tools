#!/usr/bin/env python
"""nf-core: Helper tools for use with nf-core Nextflow pipelines."""

import logging
import os
import sys
from pathlib import Path

import rich
import rich.console
import rich.logging
import rich.traceback
import rich_click as click
from trogon import tui

from nf_core import __version__
from nf_core.download import DownloadError
from nf_core.modules.modules_repo import NF_CORE_MODULES_REMOTE
from nf_core.params_file import ParamsFileBuilder
from nf_core.utils import check_if_outdated, rich_force_colors, setup_nfcore_dir

# Set up logging as the root logger
# Submodules should all traverse back to this
log = logging.getLogger()

# Set up .nfcore directory for storing files between sessions
setup_nfcore_dir()

# Set up nicer formatting of click cli help messages
click.rich_click.MAX_WIDTH = 100
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.COMMAND_GROUPS = {
    "nf-core": [
        {
            "name": "Commands for users",
            "commands": [
                "list",
                "launch",
                "create-params-file",
                "download",
                "licences",
                "tui",
            ],
        },
        {
            "name": "Commands for developers",
            "commands": [
                "create",
                "lint",
                "modules",
                "subworkflows",
                "schema",
                "create-logo",
                "bump-version",
                "sync",
            ],
        },
    ],
    "nf-core modules": [
        {
            "name": "For pipelines",
            "commands": ["list", "info", "install", "update", "remove", "patch"],
        },
        {
            "name": "Developing new modules",
            "commands": ["create", "lint", "bump-versions", "test"],
        },
    ],
    "nf-core subworkflows": [
        {
            "name": "For pipelines",
            "commands": ["info", "install", "list", "remove", "update"],
        },
        {
            "name": "Developing new subworkflows",
            "commands": ["create", "test", "lint"],
        },
    ],
}
click.rich_click.OPTION_GROUPS = {
    "nf-core modules list local": [{"options": ["--dir", "--json", "--help"]}],
}

# Set up rich stderr console
stderr = rich.console.Console(stderr=True, force_terminal=rich_force_colors())
stdout = rich.console.Console(force_terminal=rich_force_colors())

# Set up the rich traceback
rich.traceback.install(console=stderr, width=200, word_wrap=True, extra_lines=1)


# Define exceptions for which no traceback should be printed,
# because they are actually preliminary, but intended program terminations.
# (Custom exceptions are cleaner than `sys.exit(1)`, which we used before)
def selective_traceback_hook(exctype, value, traceback):
    if exctype in {DownloadError}:  # extend set as needed
        log.error(value)
    else:
        # print the colored traceback for all other exceptions with rich as usual
        stderr.print(rich.traceback.Traceback.from_exception(exctype, value, traceback))


sys.excepthook = selective_traceback_hook


# Define callback function to normalize the case of click arguments,
# which is used to make the module/subworkflow names, provided by the
# user on the cli, case insensitive.
def normalize_case(ctx, param, component_name):
    if component_name is not None:
        return component_name.casefold()


def run_nf_core():
    # print nf-core header if environment variable is not set
    if os.environ.get("_NF_CORE_COMPLETE") is None:
        # Print nf-core header
        stderr.print(f"\n[green]{' ' * 42},--.[grey39]/[green],-.", highlight=False)
        stderr.print(
            "[blue]          ___     __   __   __   ___     [green]/,-._.--~\\",
            highlight=False,
        )
        stderr.print(
            r"[blue]    |\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {",
            highlight=False,
        )
        stderr.print(
            r"[blue]    | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,",
            highlight=False,
        )
        stderr.print(
            "[green]                                          `._,._,'\n",
            highlight=False,
        )
        stderr.print(
            f"[grey39]    nf-core/tools version {__version__} - [link=https://nf-co.re]https://nf-co.re[/]",
            highlight=False,
        )
        try:
            is_outdated, _, remote_vers = check_if_outdated()
            if is_outdated:
                stderr.print(
                    f"[bold bright_yellow]    There is a new version of nf-core/tools available! ({remote_vers})",
                    highlight=False,
                )
        except Exception as e:
            log.debug(f"Could not check latest version: {e}")
        stderr.print("\n")
    # Launch the click cli
    nf_core_cli(auto_envvar_prefix="NFCORE")


@tui()
@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
@click.version_option(__version__)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Print verbose output to the console.",
)
@click.option("--hide-progress", is_flag=True, default=False, help="Don't show progress bars.")
@click.option("-l", "--log-file", help="Save a verbose log to a file.", metavar="<filename>")
@click.pass_context
def nf_core_cli(ctx, verbose, hide_progress, log_file):
    """
    nf-core/tools provides a set of helper tools for use with nf-core Nextflow pipelines.

    It is designed for both end-users running pipelines and also developers creating new pipelines.
    """
    # Set the base logger to output DEBUG
    log.setLevel(logging.DEBUG)

    # Set up logs to the console
    log.addHandler(
        rich.logging.RichHandler(
            level=logging.DEBUG if verbose else logging.INFO,
            console=rich.console.Console(stderr=True, force_terminal=rich_force_colors()),
            show_time=False,
            show_path=verbose,  # True if verbose, false otherwise
            markup=True,
        )
    )

    # don't show rich debug logging in verbose mode
    rich_logger = logging.getLogger("rich")
    rich_logger.setLevel(logging.INFO)

    # Set up logs to a file if we asked for one
    if log_file:
        log_fh = logging.FileHandler(log_file, encoding="utf-8")
        log_fh.setLevel(logging.DEBUG)
        log_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)-20s [%(levelname)-7s]  %(message)s"))
        log.addHandler(log_fh)

    ctx.obj = {
        "verbose": verbose,
        "hide_progress": hide_progress or verbose,  # Always hide progress bar with verbose logging
    }


# nf-core list
@nf_core_cli.command("list")
@click.argument("keywords", required=False, nargs=-1, metavar="<filter keywords>")
@click.option(
    "-s",
    "--sort",
    type=click.Choice(["release", "pulled", "name", "stars"]),
    default="release",
    help="How to sort listed pipelines",
)
@click.option("--json", is_flag=True, default=False, help="Print full output as JSON")
@click.option("--show-archived", is_flag=True, default=False, help="Print archived workflows")
def list_pipelines(keywords, sort, json, show_archived):
    """
    List available nf-core pipelines with local info.

    Checks the web for a list of nf-core pipelines with their latest releases.
    Shows which nf-core pipelines you have pulled locally and whether they are up to date.
    """
    from nf_core.list import list_workflows

    stdout.print(list_workflows(keywords, sort, json, show_archived))


# nf-core launch
@nf_core_cli.command()
@click.argument("pipeline", required=False, metavar="<pipeline name>")
@click.option("-r", "--revision", help="Release/branch/SHA of the project to run (if remote)")
@click.option("-i", "--id", help="ID for web-gui launch parameter set")
@click.option(
    "-c",
    "--command-only",
    is_flag=True,
    default=False,
    help="Create Nextflow command with params (no params file)",
)
@click.option(
    "-o",
    "--params-out",
    type=click.Path(),
    default=os.path.join(os.getcwd(), "nf-params.json"),
    help="Path to save run parameters file",
)
@click.option(
    "-p",
    "--params-in",
    type=click.Path(exists=True),
    help="Set of input run params to use from a previous run",
)
@click.option(
    "-a",
    "--save-all",
    is_flag=True,
    default=False,
    help="Save all parameters, even if unchanged from default",
)
@click.option(
    "-x",
    "--show-hidden",
    is_flag=True,
    default=False,
    help="Show hidden params which don't normally need changing",
)
@click.option(
    "-u",
    "--url",
    type=str,
    default="https://nf-co.re/launch",
    help="Customise the builder URL (for development work)",
)
def launch(
    pipeline,
    id,
    revision,
    command_only,
    params_in,
    params_out,
    save_all,
    show_hidden,
    url,
):
    """
    Launch a pipeline using a web GUI or command line prompts.

    Uses the pipeline schema file to collect inputs for all available pipeline
    parameters. Parameter names, descriptions and help text are shown.
    The pipeline schema is used to validate all inputs as they are entered.

    When finished, saves a file with the selected parameters which can be
    passed to Nextflow using the -params-file option.

    Run using a remote pipeline name (such as GitHub `user/repo` or a URL),
    a local pipeline directory or an ID from the nf-core web launch tool.
    """
    from nf_core.launch import Launch

    launcher = Launch(
        pipeline,
        revision,
        command_only,
        params_in,
        params_out,
        save_all,
        show_hidden,
        url,
        id,
    )
    if not launcher.launch_pipeline():
        sys.exit(1)


# nf-core create-params-file
@nf_core_cli.command()
@click.argument("pipeline", required=False, metavar="<pipeline name>")
@click.option("-r", "--revision", help="Release/branch/SHA of the pipeline (if remote)")
@click.option(
    "-o",
    "--output",
    type=str,
    default="nf-params.yml",
    metavar="<filename>",
    help="Output filename. Defaults to `nf-params.yml`.",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite existing files")
@click.option(
    "-x",
    "--show-hidden",
    is_flag=True,
    default=False,
    help="Show hidden params which don't normally need changing",
)
def create_params_file(pipeline, revision, output, force, show_hidden):
    """
    Build a parameter file for a pipeline.

    Uses the pipeline schema file to generate a YAML parameters file.
    Parameters are set to the pipeline defaults and descriptions are shown in comments.
    After the output file is generated, it can then be edited as needed before
    passing to nextflow using the `-params-file` option.

    Run using a remote pipeline name (such as GitHub `user/repo` or a URL),
    a local pipeline directory.
    """
    builder = ParamsFileBuilder(pipeline, revision)

    if not builder.write_params_file(output, show_hidden=show_hidden, force=force):
        sys.exit(1)


# nf-core download
@nf_core_cli.command()
@click.argument("pipeline", required=False, metavar="<pipeline name>")
@click.option(
    "-r",
    "--revision",
    multiple=True,
    help="Pipeline release to download. Multiple invocations are possible, e.g. `-r 1.1 -r 1.2`",
)
@click.option("-o", "--outdir", type=str, help="Output directory")
@click.option(
    "-x",
    "--compress",
    type=click.Choice(["tar.gz", "tar.bz2", "zip", "none"]),
    help="Archive compression type",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite existing files")
# TODO: Remove this in a future release. Deprecated in March 2024.
@click.option(
    "-t",
    "--tower",
    is_flag=True,
    default=False,
    hidden=True,
    help="Download for Seqera Platform. DEPRECATED: Please use `--platform` instead.",
)
@click.option(
    "--platform",
    is_flag=True,
    default=False,
    help="Download for Seqera Platform (formerly Nextflow Tower)",
)
@click.option(
    "-d",
    "--download-configuration",
    is_flag=True,
    default=False,
    help="Include configuration profiles in download. Not available with `--platform`",
)
@click.option(
    "--tag",
    multiple=True,
    help="Add custom alias tags to `--platform` downloads. For example, `--tag \"3.10=validated\"` adds the custom 'validated' tag to the 3.10 release.",
)
# -c changed to -s for consistency with other --container arguments, where it is always the first letter of the last word.
# Also -c might be used instead of -d for config in a later release, but reusing params for different options in two subsequent releases might be too error-prone.
@click.option(
    "-s",
    "--container-system",
    type=click.Choice(["none", "singularity"]),
    help="Download container images of required software.",
)
@click.option(
    "-l",
    "--container-library",
    multiple=True,
    help="Container registry/library or mirror to pull images from.",
)
@click.option(
    "-u",
    "--container-cache-utilisation",
    type=click.Choice(["amend", "copy", "remote"]),
    help="Utilise a `singularity.cacheDir` in the download process, if applicable.",
)
@click.option(
    "-i",
    "--container-cache-index",
    type=str,
    help="List of images already available in a remote `singularity.cacheDir`.",
)
@click.option(
    "-p",
    "--parallel-downloads",
    type=int,
    default=4,
    help="Number of parallel image downloads",
)
def download(
    pipeline,
    revision,
    outdir,
    compress,
    force,
    tower,
    platform,
    download_configuration,
    tag,
    container_system,
    container_library,
    container_cache_utilisation,
    container_cache_index,
    parallel_downloads,
):
    """
    Download a pipeline, nf-core/configs and pipeline singularity images.

    Collects all files in a single archive and configures the downloaded
    workflow to use relative paths to the configs and singularity images.
    """
    from nf_core.download import DownloadWorkflow

    if tower:
        log.warning("[red]The `-t` / `--tower` flag is deprecated. Please use `--platform` instead.[/]")

    dl = DownloadWorkflow(
        pipeline,
        revision,
        outdir,
        compress,
        force,
        tower or platform,  # True if either specified
        download_configuration,
        tag,
        container_system,
        container_library,
        container_cache_utilisation,
        container_cache_index,
        parallel_downloads,
    )
    dl.download_workflow()


# nf-core licences
@nf_core_cli.command()
@click.argument("pipeline", required=True, metavar="<pipeline name>")
@click.option("--json", is_flag=True, default=False, help="Print output in JSON")
def licences(pipeline, json):
    """
    List software licences for a given workflow (DSL1 only).

    Checks the pipeline environment.yml file which lists all conda software packages, which is not available for DSL2 workflows. Therefore, this command only supports DSL1 workflows (for now).
    Each of these is queried against the anaconda.org API to find the licence.
    Package name, version and licence is printed to the command line.
    """
    from nf_core.licences import WorkflowLicences

    lic = WorkflowLicences(pipeline)
    lic.as_json = json
    try:
        stdout.print(lic.run_licences())
    except LookupError as e:
        log.error(e)
        sys.exit(1)


# nf-core create
@nf_core_cli.command()
@click.option(
    "-n",
    "--name",
    type=str,
    help="The name of your new pipeline",
)
@click.option("-d", "--description", type=str, help="A short description of your pipeline")
@click.option("-a", "--author", type=str, help="Name of the main author(s)")
@click.option("--version", type=str, default="1.0dev", help="The initial version number to use")
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite output directory if it already exists",
)
@click.option("-o", "--outdir", help="Output directory for new pipeline (default: pipeline name)")
@click.option("-t", "--template-yaml", help="Pass a YAML file to customize the template")
@click.option("--plain", is_flag=True, help="Use the standard nf-core template")
def create(name, description, author, version, force, outdir, template_yaml, plain):
    """
    Create a new pipeline using the nf-core template.

    Uses the nf-core template to make a skeleton Nextflow pipeline with all required
    files, boilerplate code and best-practices.
    """
    from nf_core.create import PipelineCreate

    try:
        create_obj = PipelineCreate(
            name,
            description,
            author,
            version=version,
            force=force,
            outdir=outdir,
            template_yaml_path=template_yaml,
            plain=plain,
        )
        create_obj.init_pipeline()
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core lint
@nf_core_cli.command()
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory [dim]\[default: current working directory][/]",
)
@click.option(
    "--release",
    is_flag=True,
    default=os.path.basename(os.path.dirname(os.environ.get("GITHUB_REF", "").strip(" '\""))) == "master"
    and os.environ.get("GITHUB_REPOSITORY", "").startswith("nf-core/")
    and not os.environ.get("GITHUB_REPOSITORY", "") == "nf-core/tools",
    help="Execute additional checks for release-ready workflows.",
)
@click.option(
    "-f",
    "--fix",
    type=str,
    metavar="<test>",
    multiple=True,
    help="Attempt to automatically fix specified lint test",
)
@click.option(
    "-k",
    "--key",
    type=str,
    metavar="<test>",
    multiple=True,
    help="Run only these lint tests",
)
@click.option("-p", "--show-passed", is_flag=True, help="Show passing tests on the command line")
@click.option("-i", "--fail-ignored", is_flag=True, help="Convert ignored tests to failures")
@click.option("-w", "--fail-warned", is_flag=True, help="Convert warn tests to failures")
@click.option(
    "--markdown",
    type=str,
    metavar="<filename>",
    help="File to write linting results to (Markdown)",
)
@click.option(
    "--json",
    type=str,
    metavar="<filename>",
    help="File to write linting results to (JSON)",
)
@click.option(
    "--sort-by",
    type=click.Choice(["module", "test"]),
    default="test",
    help="Sort lint output by module or test name.",
    show_default=True,
)
@click.pass_context
def lint(
    ctx,
    dir,
    release,
    fix,
    key,
    show_passed,
    fail_ignored,
    fail_warned,
    markdown,
    json,
    sort_by,
):
    """
    Check pipeline code against nf-core guidelines.

    Runs a large number of automated tests to ensure that the supplied pipeline
    meets the nf-core guidelines. Documentation of all lint tests can be found
    on the nf-core website: [link=https://nf-co.re/tools/docs/]https://nf-co.re/tools/docs/[/]

    You can ignore tests using a file called [blue].nf-core.yml[/] [i](if you have a good reason!)[/].
    See the documentation for details.
    """
    from nf_core.lint import run_linting
    from nf_core.utils import is_pipeline_directory

    # Check if pipeline directory is a pipeline
    try:
        is_pipeline_directory(dir)
    except UserWarning as e:
        log.error(e)
        sys.exit(1)

    # Run the lint tests!
    try:
        lint_obj, module_lint_obj, subworkflow_lint_obj = run_linting(
            dir,
            release,
            fix,
            key,
            show_passed,
            fail_ignored,
            fail_warned,
            sort_by,
            markdown,
            json,
            ctx.obj["hide_progress"],
        )
        swf_failed = 0
        if subworkflow_lint_obj is not None:
            swf_failed = len(subworkflow_lint_obj.failed)
        if len(lint_obj.failed) + len(module_lint_obj.failed) + swf_failed > 0:
            sys.exit(1)
    except AssertionError as e:
        log.critical(e)
        sys.exit(1)
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core modules subcommands
@nf_core_cli.group()
@click.option(
    "-g",
    "--git-remote",
    type=str,
    default=NF_CORE_MODULES_REMOTE,
    help="Remote git repo to fetch files from",
)
@click.option(
    "-b",
    "--branch",
    type=str,
    default=None,
    help="Branch of git repository hosting modules.",
)
@click.option(
    "-N",
    "--no-pull",
    is_flag=True,
    default=False,
    help="Do not pull in latest changes to local clone of modules repository.",
)
@click.pass_context
def modules(ctx, git_remote, branch, no_pull):
    """
    Commands to manage Nextflow DSL2 modules (tool wrappers).
    """
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Place the arguments in a context object
    ctx.obj["modules_repo_url"] = git_remote
    ctx.obj["modules_repo_branch"] = branch
    ctx.obj["modules_repo_no_pull"] = no_pull


# nf-core subworkflows click command
@nf_core_cli.group()
@click.option(
    "-g",
    "--git-remote",
    type=str,
    default=NF_CORE_MODULES_REMOTE,
    help="Remote git repo to fetch files from",
)
@click.option(
    "-b",
    "--branch",
    type=str,
    default=None,
    help="Branch of git repository hosting modules.",
)
@click.option(
    "-N",
    "--no-pull",
    is_flag=True,
    default=False,
    help="Do not pull in latest changes to local clone of modules repository.",
)
@click.pass_context
def subworkflows(ctx, git_remote, branch, no_pull):
    """
    Commands to manage Nextflow DSL2 subworkflows (tool wrappers).
    """
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Place the arguments in a context object
    ctx.obj["modules_repo_url"] = git_remote
    ctx.obj["modules_repo_branch"] = branch
    ctx.obj["modules_repo_no_pull"] = no_pull


# nf-core modules list subcommands
@modules.group("list")
@click.pass_context
def modules_list(ctx):
    """
    List modules in a local pipeline or remote repository.
    """
    pass


# nf-core modules list remote
@modules_list.command("remote")
@click.pass_context
@click.argument("keywords", required=False, nargs=-1, metavar="<filter keywords>")
@click.option("-j", "--json", is_flag=True, help="Print as JSON to stdout")
def modules_list_remote(ctx, keywords, json):
    """
    List modules in a remote GitHub repo [dim i](e.g [link=https://github.com/nf-core/modules]nf-core/modules[/])[/].
    """
    from nf_core.modules import ModuleList

    try:
        module_list = ModuleList(
            None,
            True,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core modules list local
@modules_list.command("local")
@click.pass_context
@click.argument("keywords", required=False, nargs=-1, metavar="<filter keywords>")
@click.option("-j", "--json", is_flag=True, help="Print as JSON to stdout")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: Current working directory][/]",
)
def modules_list_local(ctx, keywords, json, dir):  # pylint: disable=redefined-builtin
    """
    List modules installed locally in a pipeline
    """
    from nf_core.modules import ModuleList

    try:
        module_list = ModuleList(
            dir,
            False,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core modules install
@modules.command("install")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option(
    "-p",
    "--prompt",
    is_flag=True,
    default=False,
    help="Prompt for the version of the module",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force reinstallation of module if it already exists",
)
@click.option("-s", "--sha", type=str, metavar="<commit sha>", help="Install module at commit SHA")
def modules_install(ctx, tool, dir, prompt, force, sha):
    """
    Install DSL2 modules within a pipeline.

    Fetches and installs module files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.modules import ModuleInstall

    try:
        module_install = ModuleInstall(
            dir,
            force,
            prompt,
            sha,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        exit_status = module_install.install(tool)
        if not exit_status:
            sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core modules update
@modules.command("update")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    "directory",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Force update of module")
@click.option(
    "-p",
    "--prompt",
    is_flag=True,
    default=False,
    help="Prompt for the version of the module",
)
@click.option("-s", "--sha", type=str, metavar="<commit sha>", help="Install module at commit SHA")
@click.option(
    "-a",
    "--all",
    "install_all",
    is_flag=True,
    default=False,
    help="Update all modules installed in pipeline",
)
@click.option(
    "-x/-y",
    "--preview/--no-preview",
    is_flag=True,
    default=None,
    help="Preview / no preview of changes before applying",
)
@click.option(
    "-D",
    "--save-diff",
    type=str,
    metavar="<filename>",
    default=None,
    help="Save diffs to a file instead of updating in place",
)
@click.option(
    "-u",
    "--update-deps",
    is_flag=True,
    default=False,
    help="Automatically update all linked modules and subworkflows without asking for confirmation",
)
def modules_update(
    ctx,
    tool,
    directory,
    force,
    prompt,
    sha,
    install_all,
    preview,
    save_diff,
    update_deps,
):
    """
    Update DSL2 modules within a pipeline.

    Fetches and updates module files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.modules import ModuleUpdate

    try:
        module_install = ModuleUpdate(
            directory,
            force,
            prompt,
            sha,
            install_all,
            preview,
            save_diff,
            update_deps,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        exit_status = module_install.update(tool)
        if not exit_status and install_all:
            sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core modules patch
@modules.command()
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option("-r", "--remove", is_flag=True, default=False)
def patch(ctx, tool, dir, remove):
    """
    Create a patch file for minor changes in a module

    Checks if a module has been modified locally and creates a patch file
    describing how the module has changed from the remote version
    """
    from nf_core.modules import ModulePatch

    try:
        module_patch = ModulePatch(
            dir,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        if remove:
            module_patch.remove(tool)
        else:
            module_patch.patch(tool)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core modules remove
@modules.command("remove")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
def modules_remove(ctx, dir, tool):
    """
    Remove a module from a pipeline.
    """
    from nf_core.modules import ModuleRemove

    try:
        module_remove = ModuleRemove(
            dir,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        module_remove.remove(tool)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core modules create
@modules.command("create")
@click.pass_context
@click.argument("tool", type=str, required=False, metavar="<tool> or <tool/subtool>")
@click.option("-d", "--dir", type=click.Path(exists=True), default=".", metavar="<directory>")
@click.option(
    "-a",
    "--author",
    type=str,
    metavar="<author>",
    help="Module author's GitHub username prefixed with '@'",
)
@click.option(
    "-l",
    "--label",
    type=str,
    metavar="<process label>",
    help="Standard resource label for process",
)
@click.option(
    "-m",
    "--meta",
    is_flag=True,
    default=False,
    help="Use Groovy meta map for sample information",
)
@click.option(
    "-n",
    "--no-meta",
    is_flag=True,
    default=False,
    help="Don't use meta map for sample information",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite any files if they already exist",
)
@click.option(
    "-c",
    "--conda-name",
    type=str,
    default=None,
    help="Name of the conda package to use",
)
@click.option(
    "-p",
    "--conda-package-version",
    type=str,
    default=None,
    help="Version of conda package to use",
)
@click.option(
    "-i",
    "--empty-template",
    is_flag=True,
    default=False,
    help="Create a module from the template without TODOs or examples",
)
@click.option(
    "--migrate-pytest",
    is_flag=True,
    default=False,
    help="Migrate a module with pytest tests to nf-test",
)
def create_module(
    ctx,
    tool,
    dir,
    author,
    label,
    meta,
    no_meta,
    force,
    conda_name,
    conda_package_version,
    empty_template,
    migrate_pytest,
):
    """
    Create a new DSL2 module from the nf-core template.

    If the specified directory is a pipeline, this function creates a file called
    'modules/local/tool_subtool.nf'

    If the specified directory is a clone of nf-core/modules, it creates or modifies files
    in 'modules/', 'tests/modules' and 'tests/config/pytest_modules.yml'
    """
    # Combine two bool flags into one variable
    has_meta = None
    if meta and no_meta:
        log.critical("Both arguments '--meta' and '--no-meta' given. Please pick one.")
    elif meta:
        has_meta = True
    elif no_meta:
        has_meta = False

    from nf_core.modules import ModuleCreate

    # Run function
    try:
        module_create = ModuleCreate(
            dir,
            tool,
            author,
            label,
            has_meta,
            force,
            conda_name,
            conda_package_version,
            empty_template,
            migrate_pytest,
        )
        module_create.create()
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)
    except LookupError as e:
        log.error(e)
        sys.exit(1)


# nf-core modules test
@modules.command("test")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    metavar="<nf-core/modules directory>",
)
@click.option(
    "-p",
    "--no-prompts",
    is_flag=True,
    default=False,
    help="Use defaults without prompting",
)
@click.option("-u", "--update", is_flag=True, default=False, help="Update existing snapshots")
@click.option(
    "-o",
    "--once",
    is_flag=True,
    default=False,
    help="Run tests only once. Don't check snapshot stability",
)
@click.option(
    "--profile",
    type=click.Choice(["docker", "singularity", "conda"]),
    default=None,
    help="Run tests with a specific profile",
)
def test_module(ctx, tool, dir, no_prompts, update, once, profile):
    """
    Run nf-test for a module.

    Given the name of a module, runs the nf-test command to test the module and generate snapshots.
    """
    from nf_core.components.components_test import ComponentsTest

    try:
        module_tester = ComponentsTest(
            component_type="modules",
            component_name=tool,
            directory=dir,
            no_prompts=no_prompts,
            update=update,
            once=once,
            remote_url=ctx.obj["modules_repo_url"],
            branch=ctx.obj["modules_repo_branch"],
            verbose=ctx.obj["verbose"],
            profile=profile,
        )
        module_tester.run()
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core modules lint
@modules.command("lint")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    metavar="<pipeline/modules directory>",
)
@click.option(
    "-r",
    "--registry",
    type=str,
    metavar="<registry>",
    default=None,
    help="Registry to use for containers. If not specified it will use docker.registry value in the nextflow.config file",
)
@click.option(
    "-k",
    "--key",
    type=str,
    metavar="<test>",
    multiple=True,
    help="Run only these lint tests",
)
@click.option("-a", "--all", is_flag=True, help="Run on all modules")
@click.option("-w", "--fail-warned", is_flag=True, help="Convert warn tests to failures")
@click.option("--local", is_flag=True, help="Run additional lint tests for local modules")
@click.option("--passed", is_flag=True, help="Show passed tests")
@click.option(
    "--sort-by",
    type=click.Choice(["module", "test"]),
    default="test",
    help="Sort lint output by module or test name.",
    show_default=True,
)
@click.option(
    "--fix-version",
    is_flag=True,
    help="Fix the module version if a newer version is available",
)
def modules_lint(ctx, tool, dir, registry, key, all, fail_warned, local, passed, sort_by, fix_version):
    """
    Lint one or more modules in a directory.

    Checks DSL2 module code against nf-core guidelines to ensure
    that all modules follow the same standards.

    Test modules within a pipeline or a clone of the
    nf-core/modules repository.
    """
    from nf_core.components.lint import LintExceptionError
    from nf_core.modules import ModuleLint

    try:
        module_lint = ModuleLint(
            dir,
            fail_warned=fail_warned,
            registry=ctx.params["registry"],
            remote_url=ctx.obj["modules_repo_url"],
            branch=ctx.obj["modules_repo_branch"],
            no_pull=ctx.obj["modules_repo_no_pull"],
            hide_progress=ctx.obj["hide_progress"],
        )
        module_lint.lint(
            module=tool,
            registry=registry,
            key=key,
            all_modules=all,
            print_results=True,
            local=local,
            show_passed=passed,
            sort_by=sort_by,
            fix_version=fix_version,
        )
        if len(module_lint.failed) > 0:
            sys.exit(1)
    except LintExceptionError as e:
        log.error(e)
        sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core modules info
@modules.command("info")
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: Current working directory][/]",
)
def modules_info(ctx, tool, dir):
    """
    Show developer usage information about a given module.

    Parses information from a module's [i]meta.yml[/] and renders help
    on the command line. A handy equivalent to searching the
    [link=https://nf-co.re/modules]nf-core website[/].

    If run from a pipeline and a local copy of the module is found, the command
    will print this usage info.
    If not, usage from the remote modules repo will be shown.
    """
    from nf_core.modules import ModuleInfo

    try:
        module_info = ModuleInfo(
            dir,
            tool,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_info.get_component_info())
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core modules bump-versions
@modules.command()
@click.pass_context
@click.argument("tool", type=str, callback=normalize_case, required=False, metavar="<tool> or <tool/subtool>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    metavar="<nf-core/modules directory>",
)
@click.option("-a", "--all", is_flag=True, help="Run on all modules")
@click.option("-s", "--show-all", is_flag=True, help="Show up-to-date modules in results too")
def bump_versions(ctx, tool, dir, all, show_all):
    """
    Bump versions for one or more modules in a clone of
    the nf-core/modules repo.
    """
    from nf_core.modules.bump_versions import ModuleVersionBumper
    from nf_core.modules.modules_utils import ModuleExceptionError

    try:
        version_bumper = ModuleVersionBumper(
            dir,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        version_bumper.bump_versions(module=tool, all_modules=all, show_uptodate=show_all)
    except ModuleExceptionError as e:
        log.error(e)
        sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core subworkflows create
@subworkflows.command("create")
@click.pass_context
@click.argument("subworkflow", type=str, required=False, metavar="subworkflow name")
@click.option("-d", "--dir", type=click.Path(exists=True), default=".", metavar="<directory>")
@click.option(
    "-a",
    "--author",
    type=str,
    metavar="<author>",
    help="Module author's GitHub username prefixed with '@'",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite any files if they already exist",
)
@click.option(
    "--migrate-pytest",
    is_flag=True,
    default=False,
    help="Migrate a module with pytest tests to nf-test",
)
def create_subworkflow(ctx, subworkflow, dir, author, force, migrate_pytest):
    """
    Create a new subworkflow from the nf-core template.

    If the specified directory is a pipeline, this function creates a file called
    'subworkflows/local/<subworkflow_name>.nf'

    If the specified directory is a clone of nf-core/modules, it creates or modifies files
    in 'subworkflows/', 'tests/subworkflows' and 'tests/config/pytest_modules.yml'
    """
    from nf_core.subworkflows import SubworkflowCreate

    # Run function
    try:
        subworkflow_create = SubworkflowCreate(dir, subworkflow, author, force, migrate_pytest)
        subworkflow_create.create()
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)
    except LookupError as e:
        log.error(e)
        sys.exit(1)


# nf-core subworkflows test
@subworkflows.command("test")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    metavar="<nf-core/modules directory>",
)
@click.option(
    "-p",
    "--no-prompts",
    is_flag=True,
    default=False,
    help="Use defaults without prompting",
)
@click.option("-u", "--update", is_flag=True, default=False, help="Update existing snapshots")
@click.option(
    "-o",
    "--once",
    is_flag=True,
    default=False,
    help="Run tests only once. Don't check snapshot stability",
)
@click.option(
    "--profile",
    type=click.Choice(["none", "singularity"]),
    default=None,
    help="Run tests with a specific profile",
)
def test_subworkflow(ctx, subworkflow, dir, no_prompts, update, once, profile):
    """
    Run nf-test for a subworkflow.

    Given the name of a subworkflow, runs the nf-test command to test the subworkflow and generate snapshots.
    """
    from nf_core.components.components_test import ComponentsTest

    try:
        sw_tester = ComponentsTest(
            component_type="subworkflows",
            component_name=subworkflow,
            directory=dir,
            no_prompts=no_prompts,
            update=update,
            once=once,
            remote_url=ctx.obj["modules_repo_url"],
            branch=ctx.obj["modules_repo_branch"],
            verbose=ctx.obj["verbose"],
            profile=profile,
        )
        sw_tester.run()
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core subworkflows list subcommands
@subworkflows.group("list")
@click.pass_context
def subworkflows_list(ctx):
    """
    List subworkflows in a local pipeline or remote repository.
    """
    pass


# nf-core subworkflows list remote
@subworkflows_list.command("remote")
@click.pass_context
@click.argument("keywords", required=False, nargs=-1, metavar="<filter keywords>")
@click.option("-j", "--json", is_flag=True, help="Print as JSON to stdout")
def subworkflows_list_remote(ctx, keywords, json):
    """
    List subworkflows in a remote GitHub repo [dim i](e.g [link=https://github.com/nf-core/modules]nf-core/modules[/])[/].
    """
    from nf_core.subworkflows import SubworkflowList

    try:
        subworkflow_list = SubworkflowList(
            None,
            True,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )

        stdout.print(subworkflow_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core subworkflows list local
@subworkflows_list.command("local")
@click.pass_context
@click.argument("keywords", required=False, nargs=-1, metavar="<filter keywords>")
@click.option("-j", "--json", is_flag=True, help="Print as JSON to stdout")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: Current working directory][/]",
)
def subworkflows_list_local(ctx, keywords, json, dir):  # pylint: disable=redefined-builtin
    """
    List subworkflows installed locally in a pipeline
    """
    from nf_core.subworkflows import SubworkflowList

    try:
        subworkflow_list = SubworkflowList(
            dir,
            False,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(subworkflow_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core subworkflows lint
@subworkflows.command("lint")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    metavar="<pipeline/modules directory>",
)
@click.option(
    "-r",
    "--registry",
    type=str,
    metavar="<registry>",
    default=None,
    help="Registry to use for containers. If not specified it will use docker.registry value in the nextflow.config file",
)
@click.option(
    "-k",
    "--key",
    type=str,
    metavar="<test>",
    multiple=True,
    help="Run only these lint tests",
)
@click.option("-a", "--all", is_flag=True, help="Run on all subworkflows")
@click.option("-w", "--fail-warned", is_flag=True, help="Convert warn tests to failures")
@click.option("--local", is_flag=True, help="Run additional lint tests for local subworkflows")
@click.option("--passed", is_flag=True, help="Show passed tests")
@click.option(
    "--sort-by",
    type=click.Choice(["subworkflow", "test"]),
    default="test",
    help="Sort lint output by subworkflow or test name.",
    show_default=True,
)
def subworkflows_lint(ctx, subworkflow, dir, registry, key, all, fail_warned, local, passed, sort_by):
    """
    Lint one or more subworkflows in a directory.

    Checks DSL2 subworkflow code against nf-core guidelines to ensure
    that all subworkflows follow the same standards.

    Test subworkflows within a pipeline or a clone of the
    nf-core/modules repository.
    """
    from nf_core.components.lint import LintExceptionError
    from nf_core.subworkflows import SubworkflowLint

    try:
        subworkflow_lint = SubworkflowLint(
            dir,
            fail_warned=fail_warned,
            registry=ctx.params["registry"],
            remote_url=ctx.obj["modules_repo_url"],
            branch=ctx.obj["modules_repo_branch"],
            no_pull=ctx.obj["modules_repo_no_pull"],
            hide_progress=ctx.obj["hide_progress"],
        )
        subworkflow_lint.lint(
            subworkflow=subworkflow,
            registry=registry,
            key=key,
            all_subworkflows=all,
            print_results=True,
            local=local,
            show_passed=passed,
            sort_by=sort_by,
        )
        if len(subworkflow_lint.failed) > 0:
            sys.exit(1)
    except LintExceptionError as e:
        log.error(e)
        sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core subworkflows info
@subworkflows.command("info")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: Current working directory][/]",
)
def subworkflows_info(ctx, subworkflow, dir):
    """
    Show developer usage information about a given subworkflow.

    Parses information from a subworkflow's [i]meta.yml[/] and renders help
    on the command line. A handy equivalent to searching the
    [link=https://nf-co.re/modules]nf-core website[/].

    If run from a pipeline and a local copy of the subworkflow is found, the command
    will print this usage info.
    If not, usage from the remote subworkflows repo will be shown.
    """
    from nf_core.subworkflows import SubworkflowInfo

    try:
        subworkflow_info = SubworkflowInfo(
            dir,
            subworkflow,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(subworkflow_info.get_component_info())
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core subworkflows install
@subworkflows.command("install")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option(
    "-p",
    "--prompt",
    is_flag=True,
    default=False,
    help="Prompt for the version of the subworkflow",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Force reinstallation of subworkflow if it already exists",
)
@click.option(
    "-s",
    "--sha",
    type=str,
    metavar="<commit sha>",
    help="Install subworkflow at commit SHA",
)
def subworkflows_install(ctx, subworkflow, dir, prompt, force, sha):
    """
    Install DSL2 subworkflow within a pipeline.

    Fetches and installs subworkflow files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.subworkflows import SubworkflowInstall

    try:
        subworkflow_install = SubworkflowInstall(
            dir,
            force,
            prompt,
            sha,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        exit_status = subworkflow_install.install(subworkflow)
        if not exit_status:
            sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core subworkflows remove
@subworkflows.command("remove")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
def subworkflows_remove(ctx, dir, subworkflow):
    """
    Remove a subworkflow from a pipeline.
    """
    from nf_core.subworkflows import SubworkflowRemove

    try:
        module_remove = SubworkflowRemove(
            dir,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        module_remove.remove(subworkflow)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


# nf-core subworkflows update
@subworkflows.command("update")
@click.pass_context
@click.argument("subworkflow", type=str, callback=normalize_case, required=False, metavar="subworkflow name")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Force update of subworkflow")
@click.option(
    "-p",
    "--prompt",
    is_flag=True,
    default=False,
    help="Prompt for the version of the subworkflow",
)
@click.option(
    "-s",
    "--sha",
    type=str,
    metavar="<commit sha>",
    help="Install subworkflow at commit SHA",
)
@click.option(
    "-a",
    "--all",
    "install_all",
    is_flag=True,
    default=False,
    help="Update all subworkflow installed in pipeline",
)
@click.option(
    "-x/-y",
    "--preview/--no-preview",
    is_flag=True,
    default=None,
    help="Preview / no preview of changes before applying",
)
@click.option(
    "-D",
    "--save-diff",
    type=str,
    metavar="<filename>",
    default=None,
    help="Save diffs to a file instead of updating in place",
)
@click.option(
    "-u",
    "--update-deps",
    is_flag=True,
    default=False,
    help="Automatically update all linked modules and subworkflows without asking for confirmation",
)
def subworkflows_update(
    ctx,
    subworkflow,
    dir,
    force,
    prompt,
    sha,
    install_all,
    preview,
    save_diff,
    update_deps,
):
    """
    Update DSL2 subworkflow within a pipeline.

    Fetches and updates subworkflow files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.subworkflows import SubworkflowUpdate

    try:
        subworkflow_install = SubworkflowUpdate(
            dir,
            force,
            prompt,
            sha,
            install_all,
            preview,
            save_diff,
            update_deps,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        exit_status = subworkflow_install.update(subworkflow)
        if not exit_status and install_all:
            sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


# nf-core schema subcommands
@nf_core_cli.group()
def schema():
    """
    Suite of tools for developers to manage pipeline schema.

    All nf-core pipelines should have a nextflow_schema.json file in their
    root directory that describes the different pipeline parameters.
    """
    pass


# nf-core schema validate
@schema.command()
@click.argument("pipeline", required=True, metavar="<pipeline name>")
@click.argument("params", type=click.Path(exists=True), required=True, metavar="<JSON params file>")
def validate(pipeline, params):
    """
    Validate a set of parameters against a pipeline schema.

    Nextflow can be run using the -params-file flag, which loads
    script parameters from a JSON file.

    This command takes such a file and validates it against the pipeline
    schema, checking whether all schema rules are satisfied.
    """
    from nf_core.schema import PipelineSchema

    schema_obj = PipelineSchema()
    try:
        schema_obj.get_schema_path(pipeline)
        # Load and check schema
        schema_obj.load_lint_schema()
    except AssertionError as e:
        log.error(e)
        sys.exit(1)
    schema_obj.load_input_params(params)
    try:
        schema_obj.validate_params()
    except AssertionError:
        sys.exit(1)


# nf-core schema build
@schema.command()
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option(
    "--no-prompts",
    is_flag=True,
    help="Do not confirm changes, just update parameters and exit",
)
@click.option(
    "--web-only",
    is_flag=True,
    help="Skip building using Nextflow config, just launch the web tool",
)
@click.option(
    "--url",
    type=str,
    default="https://nf-co.re/pipeline_schema_builder",
    help="Customise the builder URL (for development work)",
)
def build(dir, no_prompts, web_only, url):
    """
    Interactively build a pipeline schema from Nextflow params.

    Automatically detects parameters from the pipeline config and main.nf and
    compares these to the pipeline schema. Prompts to add or remove parameters
    if the two do not match one another.

    Once all parameters are accounted for, can launch a web GUI tool on the
    https://nf-co.re website where you can annotate and organise parameters.
    Listens for this to be completed and saves the updated schema.
    """
    from nf_core.schema import PipelineSchema

    try:
        schema_obj = PipelineSchema()
        if schema_obj.build_schema(dir, no_prompts, web_only, url) is False:
            sys.exit(1)
    except (UserWarning, AssertionError) as e:
        log.error(e)
        sys.exit(1)


# nf-core schema lint
@schema.command("lint")
@click.argument(
    "schema_path",
    type=click.Path(exists=True),
    default="nextflow_schema.json",
    metavar="<pipeline schema>",
)
def schema_lint(schema_path):
    """
    Check that a given pipeline schema is valid.

    Checks whether the pipeline schema validates as JSON Schema Draft 7
    and adheres to the additional nf-core schema requirements.

    This function runs as part of the nf-core lint command, this is a convenience
    command that does just the schema linting nice and quickly.

    If no schema path is provided, "nextflow_schema.json" will be used (if it exists).
    """
    from nf_core.schema import PipelineSchema

    schema_obj = PipelineSchema()
    try:
        schema_obj.get_schema_path(schema_path)
        schema_obj.load_lint_schema()
        # Validate title and description - just warnings as schema should still work fine
        try:
            schema_obj.validate_schema_title_description()
        except AssertionError as e:
            log.warning(e)
    except AssertionError:
        sys.exit(1)


@schema.command()
@click.argument(
    "schema_path",
    type=click.Path(exists=True),
    default="nextflow_schema.json",
    required=False,
    metavar="<pipeline schema>",
)
@click.option(
    "-o",
    "--output",
    type=str,
    metavar="<filename>",
    help="Output filename. Defaults to standard out.",
)
@click.option(
    "-x",
    "--format",
    type=click.Choice(["markdown", "html"]),
    default="markdown",
    help="Format to output docs in.",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite existing files")
@click.option(
    "-c",
    "--columns",
    type=str,
    metavar="<columns_list>",
    help="CSV list of columns to include in the parameter tables (parameter,description,type,default,required,hidden)",
    default="parameter,description,type,default,required,hidden",
)
def docs(schema_path, output, format, force, columns):
    """
    Outputs parameter documentation for a pipeline schema.
    """
    if not os.path.exists(schema_path):
        log.error("Could not find 'nextflow_schema.json' in current directory. Please specify a path.")
        sys.exit(1)

    from nf_core.schema import PipelineSchema

    schema_obj = PipelineSchema()
    # Assume we're in a pipeline dir root if schema path not set
    schema_obj.get_schema_path(schema_path)
    schema_obj.load_schema()
    schema_obj.print_documentation(output, format, force, columns.split(","))


# nf-core bump-version
@nf_core_cli.command("bump-version")
@click.argument("new_version", required=True, metavar="<new version>")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option(
    "-n",
    "--nextflow",
    is_flag=True,
    default=False,
    help="Bump required nextflow version instead of pipeline version",
)
def bump_version(new_version, dir, nextflow):
    """
    Update nf-core pipeline version number.

    The pipeline version number is mentioned in a lot of different places
    in nf-core pipelines. This tool updates the version for you automatically,
    so that you don't accidentally miss any.

    Should be used for each pipeline release, and again for the next
    development version after release.

    As well as the pipeline version, you can also change the required version of Nextflow.
    """
    from nf_core.bump_version import bump_nextflow_version, bump_pipeline_version
    from nf_core.utils import Pipeline, is_pipeline_directory

    try:
        # Check if pipeline directory contains necessary files
        is_pipeline_directory(dir)

        # Make a pipeline object and load config etc
        pipeline_obj = Pipeline(dir)
        pipeline_obj._load()

        # Bump the pipeline version number
        if not nextflow:
            bump_pipeline_version(pipeline_obj, new_version)
        else:
            bump_nextflow_version(pipeline_obj, new_version)
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core create-logo
@nf_core_cli.command("create-logo")
@click.argument("logo-text", metavar="<logo_text>")
@click.option("-d", "--dir", type=click.Path(), default=".", help="Directory to save the logo in.")
@click.option(
    "-n",
    "--name",
    type=str,
    help="Name of the output file (with or without '.png' suffix).",
)
@click.option(
    "--theme",
    type=click.Choice(["light", "dark"]),
    default="light",
    help="Theme for the logo.",
    show_default=True,
)
@click.option(
    "--width",
    type=int,
    default=2300,
    help="Width of the logo in pixels.",
    show_default=True,
)
@click.option(
    "--format",
    type=click.Choice(["png", "svg"]),
    default="png",
    help="Image format of the logo, either PNG or SVG.",
    show_default=True,
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite any files if they already exist",
)
def logo(logo_text, dir, name, theme, width, format, force):
    """
    Generate a logo with the nf-core logo template.

    This command generates an nf-core pipeline logo, using the supplied <logo_text>
    """
    from nf_core.create_logo import create_logo

    try:
        if dir == ".":
            dir = Path.cwd()
        logo_path = create_logo(logo_text, dir, name, theme, width, format, force)
        # Print path to logo relative to current working directory
        try:
            logo_path = Path(logo_path).relative_to(Path.cwd())
        except ValueError:
            logo_path = Path(logo_path)
        log.info(f"Created logo: [magenta]{logo_path}[/]")
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core sync
@nf_core_cli.command("sync")
@click.option(
    "-d",
    "--dir",
    type=click.Path(exists=True),
    default=".",
    help=r"Pipeline directory. [dim]\[default: current working directory][/]",
)
@click.option(
    "-b",
    "--from-branch",
    type=str,
    help="The git branch to use to fetch workflow variables.",
)
@click.option(
    "-p",
    "--pull-request",
    is_flag=True,
    default=False,
    help="Make a GitHub pull-request with the changes.",
)
@click.option(
    "--force_pr",
    is_flag=True,
    default=False,
    help="Force the creation of a pull-request, even if there are no changes.",
)
@click.option("-g", "--github-repository", type=str, help="GitHub PR: target repository.")
@click.option("-u", "--username", type=str, help="GitHub PR: auth username.")
@click.option("-t", "--template-yaml", help="Pass a YAML file to customize the template")
def sync(dir, from_branch, pull_request, github_repository, username, template_yaml, force_pr):
    """
    Sync a pipeline [cyan i]TEMPLATE[/] branch with the nf-core template.

    To keep nf-core pipelines up to date with improvements in the main
    template, we use a method of synchronisation that uses a special
    git branch called [cyan i]TEMPLATE[/].

    This command updates the [cyan i]TEMPLATE[/] branch with the latest version of
    the nf-core template, so that these updates can be synchronised with
    the pipeline. It is run automatically for all pipelines when ever a
    new release of [link=https://github.com/nf-core/tools]nf-core/tools[/link] (and the included template) is made.
    """
    from nf_core.sync import PipelineSync, PullRequestExceptionError, SyncExceptionError
    from nf_core.utils import is_pipeline_directory

    # Check if pipeline directory contains necessary files
    is_pipeline_directory(dir)

    # Sync the given pipeline dir
    sync_obj = PipelineSync(dir, from_branch, pull_request, github_repository, username, template_yaml, force_pr)
    try:
        sync_obj.sync()
    except (SyncExceptionError, PullRequestExceptionError) as e:
        log.error(e)
        sys.exit(1)


# Main script is being run - launch the CLI
if __name__ == "__main__":
    run_nf_core()
