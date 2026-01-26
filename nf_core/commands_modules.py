import logging
import sys

import rich

from nf_core.utils import CONTAINER_PLATFORMS, rich_force_colors

log = logging.getLogger(__name__)
stdout = rich.console.Console(force_terminal=rich_force_colors())


def modules_list_remote(ctx, keywords, json):
    """
    List modules in a remote GitHub repo [dim i](e.g [link=https://github.com/nf-core/modules]nf-core/modules[/])[/].
    """
    from nf_core.modules.list import ModuleList

    try:
        module_list = ModuleList(
            ".",
            True,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


def modules_list_local(ctx, keywords, json, directory):  # pylint: disable=redefined-builtin
    """
    List modules installed locally in a pipeline
    """
    from nf_core.modules.list import ModuleList

    try:
        module_list = ModuleList(
            directory,
            False,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_list.list_components(keywords, json))
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


def modules_install(ctx, tool, directory, prompt, force, sha):
    """
    Install DSL2 modules within a pipeline.

    Fetches and installs module files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.modules.install import ModuleInstall

    try:
        module_install = ModuleInstall(
            directory,
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
    limit_output,
):
    """
    Update DSL2 modules within a pipeline.

    Fetches and updates module files from a remote repo e.g. nf-core/modules.
    """
    from nf_core.modules.update import ModuleUpdate

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
            limit_output,
        )
        exit_status = module_install.update(tool)
        if not exit_status and install_all:
            sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


def modules_patch(ctx, tool, directory, remove):
    """
    Create a patch file for minor changes in a module

    Checks if a module has been modified locally and creates a patch file
    describing how the module has changed from the remote version
    """
    from nf_core.modules.patch import ModulePatch

    try:
        module_patch = ModulePatch(
            directory,
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


def modules_remove(ctx, directory, tool):
    """
    Remove a module from a pipeline.
    """
    from nf_core.modules.remove import ModuleRemove

    try:
        module_remove = ModuleRemove(
            directory,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        module_remove.remove(tool)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


def modules_create(
    ctx,
    tool,
    directory,
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
    in 'modules/' and 'tests/modules'
    """
    # Combine two bool flags into one variable
    has_meta = None
    if meta and no_meta:
        log.critical("Both arguments '--meta' and '--no-meta' given. Please pick one.")
    elif meta:
        has_meta = True
    elif no_meta:
        has_meta = False

    from nf_core.modules.create import ModuleCreate

    # Run function
    try:
        module_create = ModuleCreate(
            directory,
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


def modules_test(ctx, tool, directory, no_prompts, update, once, profile, migrate_pytest):
    """
    Run nf-test for a module.

    Given the name of a module, runs the nf-test command to test the module and generate snapshots.
    """
    from nf_core.components.components_test import ComponentsTest

    if migrate_pytest:
        modules_create(
            ctx,
            tool,
            directory,
            author="",
            label="",
            meta=True,
            no_meta=False,
            force=False,
            conda_name=None,
            conda_package_version=None,
            empty_template=False,
            migrate_pytest=migrate_pytest,
        )
    try:
        module_tester = ComponentsTest(
            component_type="modules",
            component_name=tool,
            directory=directory,
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


def modules_lint(ctx, tool, directory, registry, key, all, fail_warned, local, passed, sort_by, fix_version, fix):
    """
    Lint one or more modules in a directory.

    Checks DSL2 module code against nf-core guidelines to ensure
    that all modules follow the same standards.

    Test modules within a pipeline or a clone of the
    nf-core/modules repository.
    """
    from nf_core.components.lint import LintExceptionError
    from nf_core.modules.lint import ModuleLint

    try:
        module_lint = ModuleLint(
            directory,
            fail_warned=fail_warned,
            fix=fix,
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


def modules_info(ctx, tool, directory):
    """
    Show developer usage information about a given module.

    Parses information from a module's [i]meta.yml[/] and renders help
    on the command line. A handy equivalent to searching the
    [link=https://nf-co.re/modules]nf-core website[/].

    If run from a pipeline and a local copy of the module is found, the command
    will print this usage info.
    If not, usage from the remote modules repo will be shown.
    """
    from nf_core.modules.info import ModuleInfo

    try:
        module_info = ModuleInfo(
            directory,
            tool,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        stdout.print(module_info.get_component_info())
    except (UserWarning, LookupError) as e:
        log.error(e)
        sys.exit(1)


def modules_bump_versions(ctx, tool, directory, all, show_all, dry_run):
    """
    Bump versions for one or more modules in a clone of
    the nf-core/modules repo.
    """
    from nf_core.modules.bump_versions import ModuleVersionBumper
    from nf_core.modules.modules_utils import ModuleExceptionError

    try:
        version_bumper = ModuleVersionBumper(
            directory,
            ctx.obj["modules_repo_url"],
            ctx.obj["modules_repo_branch"],
            ctx.obj["modules_repo_no_pull"],
        )
        version_bumper.bump_versions(module=tool, all_modules=all, show_up_to_date=show_all, dry_run=dry_run)
    except ModuleExceptionError as e:
        log.error(e)
        sys.exit(1)
    except (UserWarning, LookupError) as e:
        log.critical(e)
        sys.exit(1)


def modules_containers_create(ctx, module, directory, await_build: bool):
    """
    Build docker and singularity containers for linux/arm64 and linux/amd64 using wave.
    """
    import rich.progress

    from nf_core.modules.containers import ModuleContainers
    from nf_core.pipelines.lint_utils import console
    from nf_core.utils import CONTAINER_PLATFORMS, CONTAINER_SYSTEMS

    try:
        manager = ModuleContainers(module=module, directory=directory, verbose=ctx.obj["verbose"])

        # Calculate total tasks per module: (docker, singularity, conda) × (amd64, arm64)
        tasks_per_module = (len(CONTAINER_SYSTEMS) + 1) * len(CONTAINER_PLATFORMS)

        # Handle batch processing for all modules
        if manager.all_modules:
            if not manager.available_modules:
                log.error("No modules found to build containers for")
                sys.exit(1)

            log.info(f"Building containers for {len(manager.available_modules)} module(s)")
            failed_modules = []

            progress_bar = rich.progress.Progress(
                "[bold blue]{task.description}",
                rich.progress.BarColumn(bar_width=None),
                "[magenta]{task.completed} of {task.total}[reset]",
                transient=True,
                console=console,
                disable=ctx.obj["hide_progress"],
            )

            with progress_bar:
                for component in manager.available_modules:
                    module_name = component.component_name

                    # Create a task for this module
                    module_task_id = progress_bar.add_task(
                        f"[cyan]{module_name}[/cyan]",
                        total=tasks_per_module,
                    )

                    try:
                        # Create a new manager for each module
                        module_manager = ModuleContainers(
                            module=module_name, directory=directory, verbose=ctx.obj["verbose"]
                        )
                        _, success = module_manager.create(
                            await_build, progress_bar=progress_bar, task_id=module_task_id
                        )
                        if success:
                            module_manager.update_containers_in_meta()
                        else:
                            failed_modules.append(module_name)
                    except Exception as e:
                        log.error(f"✗ Failed to build containers for {module_name}: {e}")
                        failed_modules.append(module_name)
                        # Complete the progress bar for this module even on failure
                        progress_bar.update(module_task_id, completed=tasks_per_module)

            if failed_modules:
                log.warning(
                    f"Failed to build containers for {len(failed_modules)} module(s): {', '.join(failed_modules)}"
                )
            else:
                log.info("Successfully built containers for all modules")
        else:
            # Single module mode - create progress bar for single module
            progress_bar = rich.progress.Progress(
                "[bold blue]{task.description}",
                rich.progress.BarColumn(bar_width=None),
                "[magenta]{task.completed} of {task.total}[reset]",
                transient=True,
                console=console,
                disable=ctx.obj["hide_progress"],
            )

            with progress_bar:
                module_task_id = progress_bar.add_task(
                    f"[cyan]{manager.module}[/cyan]",
                    total=tasks_per_module,
                )
                _, success = manager.create(await_build, progress_bar=progress_bar, task_id=module_task_id)
                if success:
                    manager.update_containers_in_meta()
                else:
                    log.error(f"✗ Some container builds failed for {manager.module}")
                    sys.exit(1)

    except (UserWarning, LookupError, FileNotFoundError, ValueError, RuntimeError) as e:
        log.error(e)
        sys.exit(1)


def modules_containers_conda_lock(ctx, module, platform=CONTAINER_PLATFORMS[0]):
    """
    Build a Docker linux/arm64 container and fetch the conda lock file using wave.
    """
    from nf_core.modules.containers import ModuleContainers

    try:
        manager = ModuleContainers(module, ".", verbose=ctx.obj["verbose"])
        lock_file = manager.get_conda_lock_file(platform)
        stdout.print(lock_file)
    except (UserWarning, LookupError, FileNotFoundError, ValueError, RuntimeError) as e:
        log.error(e)
        sys.exit(1)


def modules_containers_list(ctx, module):
    """
    Print containers defined in a module meta.yml.
    """
    from nf_core.modules.containers import ModuleContainers

    try:
        manager = ModuleContainers(module, ".", verbose=ctx.obj["verbose"])
        containers = manager.list_containers()
        t = rich.table.Table("Container System", "Platform", "Image")
        for cs, p, img in containers:
            t.add_row(cs, p, img)
        stdout.print(t)
    except (UserWarning, LookupError, FileNotFoundError, ValueError) as e:
        log.error(e)
        sys.exit(1)


def modules_containers_lint(ctx, module):
    """
    Confirm containers are defined for the module.
    """
    from nf_core.modules.containers import ModuleContainers

    try:
        manager = ModuleContainers(module, ".", verbose=ctx.obj["verbose"])
        containers = manager.lint(module)
        stdout.print(f"Found {len(containers)} container(s) for {module}.")
    except (UserWarning, LookupError, FileNotFoundError, ValueError) as e:
        log.error(e)
        sys.exit(1)
