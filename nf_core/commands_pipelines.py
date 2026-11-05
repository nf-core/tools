import logging
import sys
from pathlib import Path

import click
from rich.console import Console

import nf_core.utils
from nf_core.utils import rich_force_colors

log = logging.getLogger(__name__)

stdout = Console(force_terminal=rich_force_colors())

## nf-core pipelines command functions ##


# nf-core pipelines create
def pipelines_create(
    ctx: click.Context,
    name: str | None,
    description: str | None,
    author: str | None,
    version: str,
    force: bool,
    outdir: Path | None,
    template_yaml: Path | None,
    organisation: str,
) -> None:
    """
    Create a new pipeline using the nf-core template.

    Uses the nf-core template to make a skeleton Nextflow pipeline with all required
    files, boilerplate code and best-practices.
    \n\n
    Run without any command line arguments to use an interactive interface.
    """
    from nf_core.pipelines.create import PipelineCreateApp
    from nf_core.pipelines.create.create import PipelineCreate

    if (name and description and author) or (template_yaml):
        # If all command arguments are used, run without the interactive interface
        try:
            create_obj = PipelineCreate(
                name,
                description,
                author,
                version=version,
                force=force,
                outdir=outdir,
                template_config=template_yaml,
                organisation=organisation,
            )
            create_obj.init_pipeline()
        except UserWarning as e:
            log.error(e)
            sys.exit(1)
    elif name or description or author or version != "1.0.0dev" or force or outdir or organisation != "nf-core":
        log.error(
            "[red]Partial arguments supplied.[/] "
            "Run without [i]any[/] arguments for an interactive interface, "
            "or with at least name + description + author to use non-interactively."
        )
        sys.exit(1)
    else:
        if not nf_core.utils.is_interactive():
            log.error(
                "No pipeline arguments provided and session is not interactive (no TTY detected). "
                "Please provide at least --name, --description, and --author to run non-interactively."
            )
            sys.exit(1)
        log.info("Launching interactive nf-core pipeline creation tool.")
        app = PipelineCreateApp()
        app.run()
        sys.exit(app.return_code or 0)


# nf-core pipelines bump-version
def pipelines_bump_version(ctx: click.Context, new_version: str, directory: Path, nextflow: bool) -> None:
    """
    Update nf-core pipeline version number.

    The pipeline version number is mentioned in a lot of different places
    in nf-core pipelines. This tool updates the version for you automatically,
    so that you don't accidentally miss any.

    Should be used for each pipeline release, and again for the next
    development version after release.

    As well as the pipeline version, you can also change the required version of Nextflow.
    """
    from nf_core.pipelines.bump_version import bump_nextflow_version, bump_pipeline_version
    from nf_core.utils import Pipeline, is_pipeline_directory

    try:
        # Check if pipeline directory contains necessary files
        is_pipeline_directory(directory)

        # Make a pipeline object and load config etc
        pipeline_obj = Pipeline(directory)
        pipeline_obj._load()

        # Bump the pipeline version number
        if not nextflow:
            bump_pipeline_version(pipeline_obj, new_version)
        else:
            bump_nextflow_version(pipeline_obj, new_version)
    except (UserWarning, ValueError) as e:
        log.error(e)
        sys.exit(1)


# nf-core pipelines containers create-configs
def pipelines_containers_create_configs(ctx: click.Context | None, directory: Path) -> None:
    """
    Regenerate the pipeline container config files.

    Scans all modules installed in the pipeline and rewrites the
    `conf/containers_*.config` files from their `meta.yml` container entries.

    Useful after resolving a template sync merge conflict in these files: the
    contents are always regenerated from scratch, so whatever they contained
    before is discarded.
    """
    from nf_core.pipelines.containers_utils import ContainerConfigs
    from nf_core.utils import is_pipeline_directory

    try:
        is_pipeline_directory(directory)
        ContainerConfigs(Path(directory)).generate_container_configs()
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core pipelines lint
def pipelines_lint(
    ctx: click.Context,
    directory: Path,
    release: bool,
    fix: tuple[str, ...],
    key: tuple[str, ...],
    show_passed: bool,
    fail_ignored: bool,
    fail_warned: bool,
    markdown: str | None,
    json: str | None,
    sort_by: str,
    plain_text: bool,
) -> None:
    """
    Check pipeline code against nf-core guidelines.

    Runs a large number of automated tests to ensure that the supplied pipeline
    meets the nf-core guidelines. Documentation of all lint tests can be found
    on the nf-core website: [link=https://nf-co.re/docs/nf-core-tools/api_reference/latest/]https://nf-co.re/docs/nf-core-tools/api_reference/latest/[/]

    You can ignore tests using a file called [blue].nf-core.yml[/] [i](if you have a good reason!)[/].
    See the documentation for details.
    """
    from nf_core.pipelines.lint import run_linting
    from nf_core.utils import is_pipeline_directory

    # Check if pipeline directory is a pipeline
    try:
        is_pipeline_directory(directory)
    except UserWarning as e:
        log.error(e)
        sys.exit(1)

    # Run the lint tests!
    try:
        lint_obj, module_lint_obj, subworkflow_lint_obj = run_linting(
            directory,
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
            plain_text,
        )
        swf_failed = 0
        module_failed = 0
        if subworkflow_lint_obj is not None:
            swf_failed = len(subworkflow_lint_obj.failed)
        if module_lint_obj is not None:
            module_failed = len(module_lint_obj.failed)
        if len(lint_obj.failed) + module_failed + swf_failed > 0:
            sys.exit(1)
    except AssertionError as e:
        log.critical(e)
        sys.exit(1)
    except (UserWarning, RuntimeError) as e:
        from rich.text import Text

        log.error(Text.from_ansi(str(e)))
        sys.exit(1)


# nf-core pipelines download
def pipelines_download(
    ctx: click.Context,
    pipeline: str | None,
    revision: tuple[str, ...],
    outdir: Path | None,
    compress_type: str | None,
    force: bool,
    platform: bool,
    download_configuration: str,
    tag: tuple[str, ...],
    container_system: str | None,
    container_library: tuple[str, ...],
    container_cache_utilisation: str | None,
    container_cache_index: Path | None,
    parallel_downloads: int,
) -> None:
    """
    Download a pipeline, nf-core/configs and pipeline singularity images.

    Collects all files in a single archive and configures the downloaded
    workflow to use relative paths to the configs and singularity images.
    """
    from nf_core.pipelines.download import DownloadWorkflow

    dl = DownloadWorkflow(
        pipeline,
        revision,
        outdir,
        compress_type=compress_type,
        force=force,
        platform=platform,
        download_configuration=download_configuration,
        additional_tags=tag,
        container_system=container_system,
        container_library=container_library,
        container_cache_utilisation=container_cache_utilisation,
        container_cache_index=container_cache_index,
        parallel=parallel_downloads,
        hide_progress=ctx.obj["hide_progress"],
    )
    dl.download_workflow()


# nf-core pipelines create-params-file
def pipelines_create_params_file(
    ctx: click.Context,
    pipeline: str | None,
    revision: str | None,
    output: str,
    force: bool,
    show_hidden: bool,
    no_prompts: bool = False,
) -> None:
    """
    Build a parameter file for a pipeline.

    Uses the pipeline schema file to generate a YAML parameters file.
    Parameters are set to the pipeline defaults and descriptions are shown in comments.
    After the output file is generated, it can then be edited as needed before
    passing to nextflow using the `-params-file` option.

    Run using a remote pipeline name (such as GitHub `user/repo` or a URL),
    a local pipeline directory.
    """
    from nf_core.pipelines.params_file import ParamsFileBuilder

    builder = ParamsFileBuilder(pipeline, revision, no_prompts)

    if not builder.write_params_file(Path(output), show_hidden=show_hidden, force=force):
        sys.exit(1)


# nf-core pipelines launch
def pipelines_launch(
    ctx: click.Context,
    pipeline: str | None,
    launch_id: str | None,
    revision: str | None,
    command_only: bool,
    params_in: Path | None,
    params_out: Path,
    save_all: bool,
    show_hidden: bool,
    url: str,
    no_prompts: bool = False,
) -> None:
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
    from nf_core.pipelines.launch import Launch

    launcher = Launch(
        pipeline,
        revision,
        command_only,
        params_in,
        params_out,
        save_all,
        show_hidden,
        url,
        launch_id,
        no_prompts,
    )
    if not launcher.launch_pipeline():
        sys.exit(1)


# nf-core pipelines list
def pipelines_list(ctx: click.Context, keywords: tuple[str, ...], sort: str, json: bool, show_archived: bool) -> None:
    """
    List available nf-core pipelines with local info.

    Checks the web for a list of nf-core pipelines with their latest releases.
    Shows which nf-core pipelines you have pulled locally and whether they are up to date.
    """
    from nf_core.pipelines.list import list_workflows

    stdout.print(list_workflows(keywords, sort, json, show_archived))


# nf-core pipelines rocrate
def pipelines_rocrate(
    ctx: click.Context,
    pipeline_dir: Path,
    json_path: Path | None,
    zip_path: Path | None,
    pipeline_version: str,
) -> None:
    from nf_core.pipelines.rocrate import ROCrate

    if json_path is None and zip_path is None:
        log.error("Either `--json_path` or `--zip_path` must be specified.")
        sys.exit(1)
    else:
        try:
            rocrate_obj = ROCrate(pipeline_dir, pipeline_version)
            rocrate_obj.create_rocrate(json_path=json_path, zip_path=zip_path)
        except (UserWarning, LookupError, FileNotFoundError) as e:
            log.error(e)
            sys.exit(1)


# nf-core pipelines sync
def pipelines_sync(
    ctx: click.Context,
    directory: Path,
    from_branch: str | None,
    pull_request: bool,
    github_repository: str | None,
    username: str | None,
    template_yaml: str | None,
    force_pr: bool,
    blog_post: str | None,
    no_prompts: bool = False,
) -> None:
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
    from nf_core.pipelines.sync import PipelineSync, PullRequestExceptionError, SyncExceptionError
    from nf_core.utils import is_pipeline_directory

    try:
        # Check if pipeline directory contains necessary files
        is_pipeline_directory(directory)
        # Sync the given pipeline dir
        sync_obj = PipelineSync(
            directory,
            from_branch,
            pull_request,
            github_repository,
            username,
            template_yaml,
            force_pr,
            blog_post,
            no_prompts,
        )
        sync_obj.sync()
    except (UserWarning, SyncExceptionError, PullRequestExceptionError) as e:
        log.error(e)
        sys.exit(1)


# nf-core pipelines create-logo
def pipelines_create_logo(
    logo_text: str,
    directory: Path,
    name: str | None,
    theme: str,
    width: int,
    img_format: str,
    force: bool,
) -> None:
    """
    Generate a logo with the nf-core logo template.

    This command generates an nf-core pipeline logo, using the supplied <logo_text>
    """
    from nf_core.pipelines.create_logo import create_logo

    try:
        directory = directory.resolve()
        logo_path = create_logo(logo_text, directory, name, theme, width, img_format, force)
        # Print path to logo relative to current working directory
        try:
            logo_path = Path(logo_path).relative_to(Path.cwd())
        except ValueError:
            logo_path = Path(logo_path)
        log.info(f"Created logo: [magenta]{logo_path}[/]")
    except UserWarning as e:
        log.error(e)
        sys.exit(1)


# nf-core pipelines schema validate
def pipelines_schema_validate(pipeline: str | Path, params: Path) -> None:
    """
    Validate a set of parameters against a pipeline schema.

    Nextflow can be run using the -params-file flag, which loads
    script parameters from a JSON file.

    This command takes such a file and validates it against the pipeline
    schema, checking whether all schema rules are satisfied.
    """
    from nf_core.pipelines.schema import PipelineSchema

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


# nf-core pipelines schema build
def pipelines_schema_build(directory: Path, no_prompts: bool, web_only: bool, url: str) -> None:
    """
    Interactively build a pipeline schema from Nextflow params.

    Automatically detects parameters from the pipeline config and main.nf and
    compares these to the pipeline schema. Prompts to add or remove parameters
    if the two do not match one another.

    Once all parameters are accounted for, can launch a web GUI tool on the
    https://nf-co.re website where you can annotate and organise parameters.
    Listens for this to be completed and saves the updated schema.
    """
    from nf_core.pipelines.schema import PipelineSchema

    try:
        schema_obj = PipelineSchema()
        if schema_obj.build_schema(directory, no_prompts, web_only, url) is False:
            sys.exit(1)
    except (UserWarning, AssertionError) as e:
        log.error(e)
        sys.exit(1)


# nf-core pipelines schema lint
def pipelines_schema_lint(schema_path: Path) -> None:
    """
    Check that a given pipeline schema is valid.

    Checks whether the pipeline schema validates as JSON Schema Draft 7
    and adheres to the additional nf-core pipelines schema requirements.

    This function runs as part of the nf-core pipelines lint command, this is a convenience
    command that does just the schema linting nice and quickly.

    If no schema path is provided, "nextflow_schema.json" will be used (if it exists).
    """
    from nf_core.pipelines.schema import PipelineSchema

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


# nf-core pipelines schema docs
def pipelines_schema_docs(schema_path: Path, output: str | None, output_format: str, force: bool, columns: str) -> None:
    """
    Outputs parameter documentation for a pipeline schema.
    """
    if not schema_path.exists():
        log.error("Could not find 'nextflow_schema.json' in current directory. Please specify a path.")
        sys.exit(1)

    from nf_core.pipelines.schema import PipelineSchema

    schema_obj = PipelineSchema()
    # Assume we're in a pipeline dir root if schema path not set
    schema_obj.get_schema_path(schema_path)
    schema_obj.load_schema()
    schema_obj.print_documentation(output, output_format, force, columns.split(","))
