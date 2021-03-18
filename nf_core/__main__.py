#!/usr/bin/env python
""" nf-core: Helper tools for use with nf-core Nextflow pipelines. """

from click.types import File
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
@click.option("-o", "--outdir", type=str, help="Output directory")
@click.option(
    "-c",
    "--compress",
    type=click.Choice(["tar.gz", "tar.bz2", "zip", "none"]),
    default="tar.gz",
    help="Archive compression type",
)
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite existing files")
@click.option("-s", "--singularity", is_flag=True, default=False, help="Download singularity images")
@click.option(
    "-c",
    "--singularity-cache",
    is_flag=True,
    default=False,
    help="Don't copy images to the output directory, don't set 'singularity.cacheDir' in workflow",
)
@click.option("-p", "--parallel-downloads", type=int, default=4, help="Number of parallel image downloads")
def download(pipeline, release, outdir, compress, force, singularity, singularity_cache, parallel_downloads):
    """
    Download a pipeline, nf-core/configs and pipeline singularity images.

    Collects all files in a single archive and configures the downloaded
    workflow to use relative paths to the configs and singularity images.
    """
    dl = nf_core.download.DownloadWorkflow(
        pipeline, release, outdir, compress, force, singularity, singularity_cache, parallel_downloads
    )
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
@click.option("--version", type=str, default="1.0dev", help="The initial version number to use")
@click.option("--no-git", is_flag=True, default=False, help="Do not initialise pipeline as new git repository")
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite output directory if it already exists")
@click.option("-o", "--outdir", type=str, help="Output directory for new pipeline (default: pipeline name)")
def create(name, description, author, version, no_git, force, outdir):
    """
    Create a new pipeline using the nf-core template.

    Uses the nf-core template to make a skeleton Nextflow pipeline with all required
    files, boilerplate code and bfest-practices.
    """
    create_obj = nf_core.create.PipelineCreate(name, description, author, version, no_git, force, outdir)
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
@click.option(
    "-f", "--fix", type=str, metavar="<test>", multiple=True, help="Attempt to automatically fix specified lint test"
)
@click.option("-p", "--show-passed", is_flag=True, help="Show passing tests on the command line")
@click.option("-i", "--fail-ignored", is_flag=True, help="Convert ignored tests to failures")
@click.option("--markdown", type=str, metavar="<filename>", help="File to write linting results to (Markdown)")
@click.option("--json", type=str, metavar="<filename>", help="File to write linting results to (JSON)")
def lint(pipeline_dir, release, fix, show_passed, fail_ignored, markdown, json):
    """
    Check pipeline code against nf-core guidelines.

    Runs a large number of automated tests to ensure that the supplied pipeline
    meets the nf-core guidelines. Documentation of all lint tests can be found
    on the nf-core website: https://nf-co.re/errors
    """

    # Run the lint tests!
    try:
        lint_obj = nf_core.lint.run_linting(pipeline_dir, release, fix, show_passed, fail_ignored, markdown, json)
        if len(lint_obj.failed) > 0:
            sys.exit(1)
    except AssertionError as e:
        log.critical(e)
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
@click.argument("pipeline_dir", type=click.Path(exists=True), required=False, metavar="(<pipeline directory>)")
@click.option("-j", "--json", is_flag=True, help="Print as JSON to stdout")
def list(ctx, pipeline_dir, json):
    """
    List available software modules.

    If a pipeline directory is given, lists all modules installed locally.

    If no pipeline directory is given, lists all currently available
    software wrappers in the nf-core/modules repository.
    """
    mods = nf_core.modules.PipelineModules()
    mods.modules_repo = ctx.obj["modules_repo_obj"]
    mods.pipeline_dir = pipeline_dir
    print(mods.list_modules(json))


@modules.command(help_priority=2)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.option("-t", "--tool", type=str, metavar="<tool> or <tool/subtool>")
def install(ctx, pipeline_dir, tool):
    """
    Add a DSL2 software wrapper module to a pipeline.

    Finds the relevant files in nf-core/modules and copies to the pipeline,
    along with associated metadata.
    """
    try:
        mods = nf_core.modules.PipelineModules()
        mods.modules_repo = ctx.obj["modules_repo_obj"]
        mods.pipeline_dir = pipeline_dir
        mods.install(tool)
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)


# TODO: Not yet implemented
# @modules.command(help_priority=3)
# @click.pass_context
# @click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
# @click.argument("tool", type=str, metavar="<tool name>")
# def update(ctx, tool, pipeline_dir):
#     """
#     Update one or all software wrapper modules.
#
#     Compares a currently installed module against what is available in nf-core/modules.
#     Fetchs files and updates all relevant files for that software wrapper.
#
#     If no module name is specified, loops through all currently installed modules.
#     If no version is specified, looks for the latest available version on nf-core/modules.
#     """
#     mods = nf_core.modules.PipelineModules()
#     mods.modules_repo = ctx.obj["modules_repo_obj"]
#     mods.pipeline_dir = pipeline_dir
#     mods.update(tool)


@modules.command(help_priority=4)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline directory>")
@click.option("-t", "--tool", type=str, metavar="<tool> or <tool/subtool>")
def remove(ctx, pipeline_dir, tool):
    """
    Remove a software wrapper from a pipeline.
    """
    try:
        mods = nf_core.modules.PipelineModules()
        mods.modules_repo = ctx.obj["modules_repo_obj"]
        mods.pipeline_dir = pipeline_dir
        mods.remove(tool)
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)


@modules.command("create", help_priority=5)
@click.pass_context
@click.argument("directory", type=click.Path(exists=True), required=True, metavar="<directory>")
@click.option("-t", "--tool", type=str, metavar="<tool> or <tool/subtool>")
@click.option("-a", "--author", type=str, metavar="<author>", help="Module author's GitHub username")
@click.option("-l", "--label", type=str, metavar="<process label>", help="Standard resource label for process")
@click.option("-m", "--meta", is_flag=True, default=False, help="Use Groovy meta map for sample information")
@click.option("-n", "--no-meta", is_flag=True, default=False, help="Don't use meta map for sample information")
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite any files if they already exist")
def create_module(ctx, directory, tool, author, label, meta, no_meta, force):
    """
    Create a new DSL2 module from the nf-core template.

    If <directory> is a pipeline, this function creates a file called
    'modules/local/tool_subtool.nf'

    If <directory> is a clone of nf-core/modules, it creates or modifies files
    in 'modules/software', 'modules/tests' and 'tests/config/pytest_software.yml'
    """
    # Combine two bool flags into one variable
    has_meta = None
    if meta and no_meta:
        log.critical("Both arguments '--meta' and '--no-meta' given. Please pick one.")
    elif meta:
        has_meta = True
    elif no_meta:
        has_meta = False

    # Run function
    try:
        module_create = nf_core.modules.ModuleCreate(directory, tool, author, label, has_meta, force)
        module_create.create()
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)


@modules.command("create-test-yml", help_priority=6)
@click.pass_context
@click.option("-t", "--tool", type=str, metavar="<tool> or <tool/subtool>")
@click.option("-r", "--run-tests", is_flag=True, default=False, help="Run the test workflows")
@click.option("-o", "--output", type=str, help="Path for output YAML file")
@click.option("-f", "--force", is_flag=True, default=False, help="Overwrite output YAML file if it already exists")
@click.option("-p", "--no-prompts", is_flag=True, default=False, help="Use defaults without prompting")
def create_test_yml(ctx, tool, run_tests, output, force, no_prompts):
    """
    Auto-generate a test.yml file for a new module.

    Given the name of a module, runs the Nextflow test command and automatically generate
    the required `test.yml` file based on the output files.
    """
    try:
        meta_builder = nf_core.modules.ModulesTestYmlBuilder(tool, run_tests, output, force, no_prompts)
        meta_builder.run()
    except UserWarning as e:
        log.critical(e)
        sys.exit(1)


@modules.command(help_priority=7)
@click.pass_context
@click.argument("pipeline_dir", type=click.Path(exists=True), required=True, metavar="<pipeline/modules directory>")
@click.option("-t", "--tool", type=str, metavar="<tool> or <tool/subtool>")
@click.option("-a", "--all", is_flag=True, metavar="Run on all discovered tools")
@click.option("--local", is_flag=True, help="Run additional lint tests for local modules")
@click.option("--passed", is_flag=True, help="Show passed tests")
def lint(ctx, pipeline_dir, tool, all, local, passed):
    """
    Lint one or more modules in a directory.

    Checks DSL2 module code against nf-core guidelines to ensure
    that all modules follow the same standards.

    Test modules within a pipeline or with your clone of the
    nf-core/modules repository.
    """
    try:
        module_lint = nf_core.modules.ModuleLint(dir=pipeline_dir)
        module_lint.lint(module=tool, all_modules=all, print_results=True, local=local, show_passed=passed)
    except nf_core.modules.lint.ModuleLintException as e:
        log.error(e)
        sys.exit(1)


## nf-core schema subcommands
@nf_core_cli.group(cls=CustomHelpOrder, help_priority=7)
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
    # Make a pipeline object and load config etc
    pipeline_obj = nf_core.utils.Pipeline(pipeline_dir)
    pipeline_obj._load()

    # Bump the pipeline version number
    if not nextflow:
        nf_core.bump_version.bump_pipeline_version(pipeline_obj, new_version)
    else:
        nf_core.bump_version.bump_nextflow_version(pipeline_obj, new_version)


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
