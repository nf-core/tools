#!/usr/bin/env python
""" nf-core: Helper tools for use with nf-core Nextflow pipelines. """

from rich import print
import click
import logging
import os
import re
import rich.console
import rich.logging
import rich.traceback
import sys

import nf_core
import nf_core.bump_version
import nf_core.create
import nf_core.download
import nf_core.launch
import nf_core.licences
import nf_core.lint
import nf_core.list
import nf_core.modules
import nf_core.schema
import nf_core.sync
import nf_core.utils

# Set up logging as the root logger
# Submodules should all traverse back to this
log = logging.getLogger()


def run_nf_core():
    # Set up the rich traceback
    rich.traceback.install(width=200, word_wrap=True)

    # Print nf-core header to STDERR
    stderr = rich.console.Console(file=sys.stderr, force_terminal=nf_core.utils.rich_force_colors())
    stderr.print("\n[green]{},--.[grey39]/[green],-.".format(" " * 42), highlight=False)
    stderr.print("[blue]          ___     __   __   __   ___     [green]/,-._.--~\\", highlight=False)
    stderr.print("[blue]    |\ | |__  __ /  ` /  \ |__) |__      [yellow]   }  {", highlight=False)
    stderr.print("[blue]    | \| |       \__, \__/ |  \ |___     [green]\`-._,-`-,", highlight=False)
    stderr.print("[green]                                          `._,._,'\n", highlight=False)
    stderr.print("[grey39]    nf-core/tools version {}".format(nf_core.__version__), highlight=False)
    try:
        is_outdated, current_vers, remote_vers = nf_core.utils.check_if_outdated()
        if is_outdated:
            stderr.print(
                "[bold bright_yellow]    There is a new version of nf-core/tools available! ({})".format(remote_vers),
                highlight=False,
            )
    except Exception as e:
        log.debug("Could not check latest version: {}".format(e))
    stderr.print("\n\n")

    # Lanch the click cli
    nf_core_cli()


# Customise the order of subcommands for --help
# https://stackoverflow.com/a/47984810/713980
class CustomHelpOrder(click.Group):
    def __init__(self, *args, **kwargs):
        self.help_priorities = {}
        super(CustomHelpOrder, self).__init__(*args, **kwargs)

    def get_help(self, ctx):
        self.list_commands = self.list_commands_for_help
        return super(CustomHelpOrder, self).get_help(ctx)

    def list_commands_for_help(self, ctx):
        """reorder the list of commands when listing the help"""
        commands = super(CustomHelpOrder, self).list_commands(ctx)
        return (c[1] for c in sorted((self.help_priorities.get(command, 1000), command) for command in commands))

    def command(self, *args, **kwargs):
        """Behaves the same as `click.Group.command()` except capture
        a priority for listing command names in help.
        """
        help_priority = kwargs.pop("help_priority", 1000)
        help_priorities = self.help_priorities

        def decorator(f):
            cmd = super(CustomHelpOrder, self).command(*args, **kwargs)(f)
            help_priorities[cmd.name] = help_priority
            return cmd

        return decorator

    def group(self, *args, **kwargs):
        """Behaves the same as `click.Group.group()` except capture
        a priority for listing command names in help.
        """
        help_priority = kwargs.pop("help_priority", 1000)
        help_priorities = self.help_priorities

        def decorator(f):
            cmd = super(CustomHelpOrder, self).command(*args, **kwargs)(f)
            help_priorities[cmd.name] = help_priority
            return cmd

        return decorator


@click.group(cls=CustomHelpOrder)
@click.version_option(nf_core.__version__)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Print verbose output to the console.")
@click.option("-l", "--log-file", help="Save a verbose log to a file.", metavar="<filename>")
def nf_core_cli(verbose, log_file):

    # Set the base logger to output DEBUG
    log.setLevel(logging.DEBUG)

    # Set up logs to the console
    log.addHandler(
        rich.logging.RichHandler(
            level=logging.DEBUG if verbose else logging.INFO,
            console=rich.console.Console(file=sys.stderr, force_terminal=nf_core.utils.rich_force_colors()),
            show_time=False,
            markup=True,
        )
    )

    # Set up logs to a file if we asked for one
    if log_file:
        log_fh = logging.FileHandler(log_file, encoding="utf-8")
        log_fh.setLevel(logging.DEBUG)
        log_fh.setFormatter(logging.Formatter("[%(asctime)s] %(name)-20s [%(levelname)-7s]  %(message)s"))
        log.addHandler(log_fh)


# nf-core list
@nf_core_cli.command(help_priority=1)
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
def list(keywords, sort, json, show_archived):
    """
    List available nf-core pipelines with local info.

    Checks the web for a list of nf-core pipelines with their latest releases.
    Shows which nf-core pipelines you have pulled locally and whether they are up to date.
    """
    print(nf_core.list.list_workflows(keywords, sort, json, show_archived))


# nf-core launch
@nf_core_cli.command(help_priority=2)
@click.argument("pipeline", required=False, metavar="<pipeline name>")
@click.option("-r", "--revision", help="Release/branch/SHA of the project to run (if remote)")
@click.option("-i", "--id", help="ID for web-gui launch parameter set")
@click.option(
    "-c", "--command-only", is_flag=True, default=False, help="Create Nextflow command with params (no params file)"
)
@click.option(
    "-o",
    "--params-out",
    type=click.Path(),
    default=os.path.join(os.getcwd(), "nf-params.json"),
    help="Path to save run parameters file",
)
@click.option(
    "-p", "--params-in", type=click.Path(exists=True), help="Set of input run params to use from a previous run"
)
@click.option(
    "-a", "--save-all", is_flag=True, default=False, help="Save all parameters, even if unchanged from default"
)
@click.option(
    "-h", "--show-hidden", is_flag=True, default=False, help="Show hidden params which don't normally need changing"
)
@click.option(
    "--url", type=str, default="https://nf-co.re/launch", help="Customise the builder URL (for development work)"
)
def launch(pipeline, id, revision, command_only, params_in, params_out, save_all, show_hidden, url):
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
    launcher = nf_core.launch.Launch(
        pipeline, revision, command_only, params_in, params_out, save_all, show_hidden, url, id
    )
    if launcher.launch_pipeline() == False:
        sys.exit(1)


# nf-core download
@nf_core_cli.command(help_priority=3)
@click.argument("pipeline", required=True, metavar="<pipeline name>")
@click.option("-r", "--release", type=str, help="Pipeline release")
@click.option("-s", "--singularity", is_flag=True, default=False, help="Download singularity containers")
@click.option("-o", "--outdir", type=str, help="Output directory")
@click.option(
    "-c",
    "--compress",
    type=click.Choice(["tar.gz", "tar.bz2", "zip", "none"]),
    default="tar.gz",
    help="Compression type",
)
def download(pipeline, release, singularity, outdir, compress):
    """
    Download a pipeline, configs and singularity container.

    Collects all workflow files and shared configs from nf-core/configs.
    Configures the downloaded workflow to use the relative path to the configs.
    """
    dl = nf_core.download.DownloadWorkflow(pipeline, release, singularity, outdir, compress)
    dl.download_workflow()


# nf-core licences
@nf_core_cli.command(help_priority=4)
@click.argument("pipeline", required=True, metavar="<pipeline name>")
@click.option("--json", is_flag=True, default=False, help="Print output in JSON")
def licences(pipeline, json):
    """
    List software licences for a given workflow.

    Checks the pipeline environment.yml file which lists all conda software packages.
    Each of these is queried against the anaconda.org API to find the licence.
    Package name, version and licence is printed to the command line.
    """
    lic = nf_core.licences.WorkflowLicences(pipeline)
    lic.as_json = json
    try:
        print(lic.run_licences())
    except LookupError as e:
        log.error(e)
        sys.exit(1)


# nf-core create
def validate_wf_name_prompt(ctx, opts, value):
    """ Force the workflow name to meet the nf-core requirements """
    if not re.match(r"^[a-z]+$", value):
        click.echo("Invalid workflow name: must be lowercase without punctuation.")
        value = click.prompt(opts.prompt)
        return validate_wf_name_prompt(ctx, opts, value)
    return value


@nf_core_cli.command(help_priority=5)
@click.option(
    "-n",
    "--name",
    prompt="Workflow Name",
    required=True,
    callback=validate_wf_name_prompt,
    type=str,
    help="The name of your new pipeline",
)
@click.option("-d", "--description", prompt=True, required=True, type=str, help="A short description of your pipeline")
@click.option("-a", "--author", prompt=True, required=True, type=str, help="Name of the main author(s)")
@click.option("--new-version", type=str, default="1.0dev", help="The initial version number to use")
@click.option("--no-git", is_flag=True, default=False, help="Do not initialise pipeline as new git repository")
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite output directory if it already exists")
@click.option("-o", "--outdir", type=str, help="Output directory for new pipeline (default: pipeline name)")
def create(name, description, author, new_version, no_git, force, outdir):
    """
    Create a new pipeline using the nf-core template.

    Uses the nf-core template to make a skeleton Nextflow pipeline with all required
    files, boilerplate code and best-practices.
    """
    create_obj = nf_core.create.PipelineCreate(name, description, author, new_version, no_git, force, outdir)
    create_obj.init_pipeline()


@nf_core_cli.command(help_priority=6)
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.option(
    "--release",
    is_flag=True,
    default=os.path.basename(os.path.dirname(os.environ.get("GITHUB_REF", "").strip(" '\""))) == "master"
    and os.environ.get("GITHUB_REPOSITORY", "").startswith("nf-core/")
    and not os.environ.get("GITHUB_REPOSITORY", "") == "nf-core/tools",
    help="Execute additional checks for release-ready workflows.",
)
@click.option("-p", "--show-passed", is_flag=True, help="Show passing tests on the command line.")
@click.option("--markdown", type=str, metavar="<filename>", help="File to write linting results to (Markdown)")
@click.option("--json", type=str, metavar="<filename>", help="File to write linting results to (JSON)")
def lint(pipeline_dir, release, show_passed, markdown, json):
    """
    Check pipeline code against nf-core guidelines.

    Runs a large number of automated tests to ensure that the supplied pipeline
    meets the nf-core guidelines. Documentation of all lint tests can be found
    on the nf-core website: https://nf-co.re/errors
    """

    # Run the lint tests!
    lint_obj = nf_core.lint.run_linting(pipeline_dir, release, show_passed, markdown, json)
    if len(lint_obj.failed) > 0:
        sys.exit(1)


## nf-core module subcommands
@nf_core_cli.group(cls=CustomHelpOrder, help_priority=7)
@click.option(
    "-r",
    "--repository",
    type=str,
    default="nf-core/modules",
    help="GitHub repository hosting software wrapper modules.",
)
@click.option("-b", "--branch", type=str, default="master", help="Modules GitHub repo git branch to use.")
@click.pass_context
def modules(ctx, repository, branch):
    """
    Work with the nf-core/modules software wrappers.

    Tools to manage DSL 2 nf-core/modules software wrapper imports.
    """
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)

    # Make repository object to pass to subcommands
    ctx.obj["modules_repo_obj"] = nf_core.modules.ModulesRepo(repository, branch)


@modules.command(help_priority=1)
@click.pass_context
def list(ctx):
    """
    List available software modules.

    Lists all currently available software wrappers in the nf-core/modules repository.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    print(mods.list_modules())


@modules.command(help_priority=2)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.argument("tool", type=str, required=True, metavar="<tool name>")
def install(ctx, pipeline_dir, tool):
    """
    Add a DSL2 software wrapper module to a pipeline.

    Given a software name, finds the relevant files in nf-core/modules
    and copies to the pipeline along with associated metadata.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    mods.pipeline_dir = pipeline_dir
    mods.install(tool)


@modules.command(help_priority=3)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.argument("tool", type=str, metavar="<tool name>")
@click.option("-f", "--force", is_flag=True, default=False, help="Force overwrite of files")
def update(ctx, tool, pipeline_dir, force):
    """
    Update one or all software wrapper modules.

    Compares a currently installed module against what is available in nf-core/modules.
    Fetchs files and updates all relevant files for that software wrapper.

    If no module name is specified, loops through all currently installed modules.
    If no version is specified, looks for the latest available version on nf-core/modules.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    mods.pipeline_dir = pipeline_dir
    mods.update(tool, force=force)


@modules.command(help_priority=4)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.argument("tool", type=str, required=True, metavar="<tool name>")
def remove(ctx, pipeline_dir, tool):
    """
    Remove a software wrapper from a pipeline.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    mods.pipeline_dir = pipeline_dir
    mods.remove(tool)


@modules.command(help_priority=5)
@click.pass_context
def check(ctx):
    """
    Check that imported module code has not been modified.

    Compares a software module against the copy on nf-core/modules.
    If any local modifications are found, the command logs an error
    and exits with a non-zero exit code.

    Use by the lint tests and automated CI to check that centralised
    software wrapper code is only modified in the central repository.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    mods.check_modules()


## nf-core schema subcommands
@nf_core_cli.group(cls=CustomHelpOrder, help_priority=8)
def schema():
    """
    Suite of tools for developers to manage pipeline schema.

    All nf-core pipelines should have a nextflow_schema.json file in their
    root directory that describes the different pipeline parameters.
    """
    pass


@schema.command(help_priority=1)
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
    schema_obj = nf_core.schema.PipelineSchema()
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
    except AssertionError as e:
        sys.exit(1)


@schema.command(help_priority=2)
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.option("--no-prompts", is_flag=True, help="Do not confirm changes, just update parameters and exit")
@click.option("--web-only", is_flag=True, help="Skip building using Nextflow config, just launch the web tool")
@click.option(
    "--url",
    type=str,
    default="https://nf-co.re/pipeline_schema_builder",
    help="Customise the builder URL (for development work)",
)
def build(pipeline_dir, no_prompts, web_only, url):
    """
    Interactively build a pipeline schema from Nextflow params.

    Automatically detects parameters from the pipeline config and main.nf and
    compares these to the pipeline schema. Prompts to add or remove parameters
    if the two do not match one another.

    Once all parameters are accounted for, can launch a web GUI tool on the
    https://nf-co.re website where you can annotate and organise parameters.
    Listens for this to be completed and saves the updated schema.
    """
    schema_obj = nf_core.schema.PipelineSchema()
    if schema_obj.build_schema(pipeline_dir, no_prompts, web_only, url) is False:
        sys.exit(1)


@schema.command(help_priority=3)
@click.argument("schema_path", type=click.Path(exists=True), required=True, metavar="<pipeline schema>")
def lint(schema_path):
    """
    Check that a given pipeline schema is valid.

    Checks whether the pipeline schema validates as JSON Schema Draft 7
    and adheres to the additional nf-core schema requirements.

    This function runs as part of the nf-core lint command, this is a convenience
    command that does just the schema linting nice and quickly.
    """
    schema_obj = nf_core.schema.PipelineSchema()
    try:
        schema_obj.get_schema_path(schema_path)
        schema_obj.load_lint_schema()
        # Validate title and description - just warnings as schema should still work fine
        try:
            schema_obj.validate_schema_title_description()
        except AssertionError as e:
            log.warning(e)
    except AssertionError as e:
        sys.exit(1)


@nf_core_cli.command("bump-version", help_priority=9)
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.argument("new_version", required=True, metavar="<new version>")
@click.option(
    "-n", "--nextflow", is_flag=True, default=False, help="Bump required nextflow version instead of pipeline version"
)
def bump_version(pipeline_dir, new_version, nextflow):
    """
    Update nf-core pipeline version number.

    The pipeline version number is mentioned in a lot of different places
    in nf-core pipelines. This tool updates the version for you automatically,
    so that you don't accidentally miss any.

    Should be used for each pipeline release, and again for the next
    development version after release.

    As well as the pipeline version, you can also change the required version of Nextflow.
    """

    # First, lint the pipeline to check everything is in order
    log.info("Running nf-core lint tests")

    # Run the lint tests
    try:
        lint_obj = nf_core.lint.PipelineLint(pipeline_dir)
        lint_obj.lint_pipeline()
    except AssertionError as e:
        log.error("Please fix lint errors before bumping versions")
        return
    if len(lint_obj.failed) > 0:
        log.error("Please fix lint errors before bumping versions")
        return

    # Bump the pipeline version number
    if not nextflow:
        nf_core.bump_version.bump_pipeline_version(lint_obj, new_version)
    else:
        nf_core.bump_version.bump_nextflow_version(lint_obj, new_version)


@nf_core_cli.command("sync", help_priority=10)
@click.argument("pipeline_dir", required=True, type=click.Path(exists=True), metavar="<pipeline directory>")
@click.option("-b", "--from-branch", type=str, help="The git branch to use to fetch workflow vars.")
@click.option("-p", "--pull-request", is_flag=True, default=False, help="Make a GitHub pull-request with the changes.")
@click.option("-r", "--repository", type=str, help="GitHub PR: target repository.")
@click.option("-u", "--username", type=str, help="GitHub PR: auth username.")
def sync(pipeline_dir, from_branch, pull_request, repository, username):
    """
    Sync a pipeline TEMPLATE branch with the nf-core template.

    To keep nf-core pipelines up to date with improvements in the main
    template, we use a method of synchronisation that uses a special
    git branch called TEMPLATE.

    This command updates the TEMPLATE branch with the latest version of
    the nf-core template, so that these updates can be synchronised with
    the pipeline. It is run automatically for all pipelines when ever a
    new release of nf-core/tools (and the included template) is made.
    """

    # Sync the given pipeline dir
    sync_obj = nf_core.sync.PipelineSync(pipeline_dir, from_branch, pull_request, repository, username)
    try:
        sync_obj.sync()
    except (nf_core.sync.SyncException, nf_core.sync.PullRequestException) as e:
        log.error(e)
        sys.exit(1)


if __name__ == "__main__":
    run_nf_core()
