"""
Bump versions for all modules on nf-core/modules
or for a single module
"""

import contextlib
import logging
import os
import re
from pathlib import Path

import yaml
from rich.box import ROUNDED
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress
from rich.table import Table

import nf_core.modules.modules_utils
import nf_core.utils
from nf_core.components.components_command import ComponentCommand
from nf_core.components.nfcore_component import NFCoreComponent
from nf_core.utils import NFCoreYamlConfig, rich_force_colors
from nf_core.utils import plural_s as _s

log = logging.getLogger(__name__)


class ModuleVersionBumper(ComponentCommand):
    def __init__(
        self,
        pipeline_dir: str | Path,
        remote_url: str | None = None,
        branch: str | None = None,
        no_pull: bool = False,
    ):
        super().__init__("modules", pipeline_dir, remote_url, branch, no_pull)

        self.up_to_date: list[tuple[str, str]] = []
        self.updated: list[tuple[str, str]] = []
        self.failed: list[tuple[str, str]] = []
        self.ignored: list[tuple[str, str]] = []
        self.show_up_to_date: bool | None = None
        self.tools_config: NFCoreYamlConfig | None

    def bump_versions(
        self,
        module: str | None = None,
        all_modules: bool = False,
        show_up_to_date: bool = False,
        dry_run: bool = False,
    ) -> list[NFCoreComponent]:
        """
        Bump the container and conda version of single module or all modules.

        If module is the name of a directory in the modules directory, all modules in that directory will be bumped.

        Looks for a bioconda tool version in the `environment.yml` file of the module and checks
        whether a more recent version is available. If yes, the pinned version
        in `environment.yml` is bumped and the Docker/Singularity containers are rebuilt from it
        with Wave.

        Args:
            module: a specific module to update
            all_modules: whether to bump versions for all modules
            show_up_to_date: whether to show up-to-date modules as well
            dry_run: whether to dry run the command

        Returns:
            list[NFCoreComponent]: the updated modules
        """
        self.up_to_date = []
        self.updated = []
        self.failed = []
        self.ignored = []
        self.show_up_to_date = show_up_to_date

        # Check modules directory structure
        self.check_modules_structure()

        # Verify that this is not a pipeline
        if not self.repo_type == "modules":
            raise nf_core.modules.modules_utils.ModuleExceptionError(
                "This command only works on the nf-core/modules repository, not on pipelines!"
            )

        # Get list of all modules
        _, nfcore_modules = nf_core.modules.modules_utils.get_installed_modules(self.directory)

        # Load the .nf-core.yml config
        _, self.tools_config = nf_core.utils.load_tools_config(self.directory)

        # Prompt for module or all
        if module is None and not all_modules:
            module = nf_core.modules.modules_utils.prompt_module_selection(
                nfcore_modules, component_type="modules", action="Bump versions for"
            )
            if module is None:
                all_modules = True

        if module:
            self.show_up_to_date = True
            if all_modules:
                raise nf_core.modules.modules_utils.ModuleExceptionError(
                    "You cannot specify a tool and request all tools to be bumped."
                )
            nfcore_modules = nf_core.modules.modules_utils.filter_modules_by_name(nfcore_modules, module)

            if len(nfcore_modules) == 0:
                raise nf_core.modules.modules_utils.ModuleExceptionError(
                    f"Could not find the specified module: '{module}'"
                )

        # mainly used for testing, return the list of nfcore_modules selected
        if dry_run:
            return nfcore_modules

        progress_bar = Progress(
            "[bold blue]{task.description}",
            BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
            transient=True,
            disable=os.environ.get("HIDE_PROGRESS", None) is not None,
        )
        modules_to_rebuild: list[NFCoreComponent] = []
        with progress_bar:
            bump_progress = progress_bar.add_task(
                "Bumping nf-core modules versions",
                total=len(nfcore_modules),
                test_name=nfcore_modules[0].component_name,
            )
            for mod in nfcore_modules:
                progress_bar.update(bump_progress, advance=1, test_name=mod.component_name)
                if self.bump_module_version(mod):
                    modules_to_rebuild.append(mod)

        if modules_to_rebuild:
            self._build_wave_containers(modules_to_rebuild)

        self._print_results()

        return nfcore_modules

    def _build_wave_containers(self, modules: list[NFCoreComponent]) -> None:
        """Rebuild the Docker/Singularity containers for ``modules`` with Seqera Wave.

        Builds from each module's (already bumped) environment.yml and updates main.nf,
        meta.yml and the conda lock files. Modules whose build fails are added to
        ``self.failed``.
        """
        from nf_core.modules.containers import ModuleContainers

        log.info(f"Building Seqera containers for {len(modules)} bumped module{_s(modules)} with Wave...")
        module_containers = ModuleContainers(
            module=None,
            directory=self.directory,
            all_modules=True,
            components=modules,
        )
        ModuleContainers.check_tower_token()
        failed_modules = module_containers.build_containers_with_progress()
        for module_name in failed_modules:
            self.failed.append(("Container build with Wave failed", module_name))

    def bump_module_version(self, module: NFCoreComponent) -> bool:
        """
        Bump the bioconda and container version of a single NFCoreComponent

        Args:
            module: NFCoreComponent

        Returns:
            True if the module's ``environment.yml`` was bumped and its containers therefore
            need rebuilding; False if it was already up to date, ignored or failed.
        """
        config_version = None
        # Extract the pinned conda dependencies from `environment.yml`. Wave rebuilds the containers
        # straight from this file, so every pinned package can be bumped - including multi-package
        # ("mulled") modules, which earlier versions had to skip because the old mulled container
        # names could not be regenerated.
        dependencies = self.get_bioconda_version(module)

        # Only channel-pinned, versioned deps (e.g. `bioconda::samtools=1.21`) can be bumped; skip
        # pip sub-dicts, unpinned deps and anything without a `channel::name=version` shape.
        conda_packages: list[tuple[str, str, str]] = []  # (channel, tool_name, current_version)
        for dep in dependencies:
            if not isinstance(dep, str):
                continue
            spec = dep.strip("'").strip('"')
            if "::" not in spec or "=" not in spec:
                continue
            channel, name_version = spec.split("::", 1)
            tool_name, current_version = name_version.split("=", 1)
            conda_packages.append((channel, tool_name, current_version))

        if not conda_packages:
            self.failed.append(("No pinned conda dependencies to bump", module.component_name))
            return False

        # Don't update if blocked in blacklist
        bump_versions_config: dict[str, str] = getattr(self.tools_config, "bump-versions", {}) or {}
        if module.component_name in bump_versions_config:
            config_version = bump_versions_config[module.component_name]
            if not config_version:
                self.ignored.append(("Omitting module due to config.", module.component_name))
                return False
            if len(conda_packages) > 1:
                # A single pinned version in the config can't be mapped onto a multi-package module
                self.failed.append(
                    ("Cannot pin a version via config for a multi-package module", module.component_name)
                )
                return False

        # Resolve the target version for every package: the latest available on Anaconda, or the
        # version pinned in the config blacklist.
        targets: list[tuple[str, str, str, str]] = []  # (channel, tool_name, current_version, target_version)
        for channel, tool_name, current_version in conda_packages:
            if config_version:
                target_version = config_version
            else:
                dep_spec = f"{channel}::{tool_name}={current_version}"
                try:
                    response = nf_core.utils.anaconda_package(dep_spec)
                except (LookupError, ValueError):
                    self.failed.append(
                        (
                            f"Conda version not specified correctly: {Path(module.environment_yml).relative_to(self.directory) if module.environment_yml else module.component_name}",
                            module.component_name,
                        )
                    )
                    return False

                # Check that the pinned version is available at all
                if current_version not in response.get("versions"):
                    self.failed.append(
                        (f"Conda package had unknown version: `{module.environment_yml}`", module.component_name)
                    )
                    return False

                target_version = response.get("latest_version")

            if target_version is None:
                continue
            targets.append((channel, tool_name, current_version, target_version))

        if not targets:
            self.up_to_date.append((f"Module version up to date: {module.component_name}", module.component_name))
            return False

        # Check 1: bump any dependency behind the latest. Wave rebuilds the containers from
        # environment.yml afterwards (see bump_versions()), updating main.nf, meta.yml and conda locks.
        outdated = [t for t in targets if t[3] != t[2]]
        if outdated:
            if not module.environment_yml:
                log.error(f"Could not read `environment.yml` of {module.component_name} module.")
                self.failed.append(("No environment.yml found to update", module.component_name))
                return False
            # Rewrite the versions in the raw file text so YAML comments (e.g. renovate hints) and
            # formatting survive - a yaml load/dump round-trip would silently drop them.
            with open(module.environment_yml) as fh:
                content = fh.read()
            for channel, tool_name, current_version, target_version in outdated:
                log.debug(f"Updating {tool_name} version for {module.component_name}")
                content = re.sub(
                    rf"({re.escape(channel)}::{re.escape(tool_name)})=[^\s'\"]+",
                    rf"\g<1>={target_version}",
                    content,
                )
                self.updated.append(
                    (f"Module updated: {tool_name} {current_version} --> {target_version}", module.component_name)
                )
            with open(module.environment_yml, "w") as fh:
                fh.write(content)
            return True

        # Check 2: environment.yml is already current, but make sure the containers were actually
        # built for every package. An earlier run may have bumped environment.yml and then been
        # interrupted before the Wave build wrote the new containers / conda locks.
        for _channel, tool_name, _current_version, target_version in targets:
            if not self._containers_built_for_version(module, tool_name, target_version):
                self.updated.append(
                    (f"Containers out of date - rebuilding for version {target_version}", module.component_name)
                )
                return True

        self.up_to_date.append((f"Module version up to date: {module.component_name}", module.component_name))
        return False

    def _containers_built_for_version(self, module: NFCoreComponent, tool_name: str, version: str) -> bool:
        """Return True if the module's Wave conda-lock files already pin ``tool_name`` at ``version``.

        Image names are content hashes, so the version-bearing conda locks are checked instead,
        assuming the bioconda dependency name matches the conda package name. No ``.conda-lock`` dir
        means the module was never Wave-built (left alone); an empty dir, or a meta.yml without a
        ``containers:`` section, means an interrupted build (rebuilt).
        """
        from nf_core.components.components_utils import read_meta_yml

        conda_lock_dir = module.component_dir / ".conda-lock"
        if not conda_lock_dir.is_dir():
            log.debug(
                f"No conda-lock directory for {module.component_name}; treating as up to date "
                "(Wave migration is out of scope for bump-versions)"
            )
            return True
        lock_files = list(conda_lock_dir.glob("*.txt"))
        if not lock_files:
            # Empty dir: a finished build always leaves locks, so this one was interrupted.
            log.debug(f"Empty conda-lock directory for {module.component_name}; containers need rebuilding")
            return False
        # Lock entries look like `.../samtools-1.21-h50ea8bc_0.conda`; trailing `-` keeps 1.21 from
        # matching 1.210. Stream each file so the search short-circuits.
        needle = f"/{tool_name}-{version}-"
        for lock_file in lock_files:
            with lock_file.open() as fh:
                if not any(needle in line for line in fh):
                    return False

        # The containers section is written last, so its absence means an interrupted build. Only
        # require it to be present, not complete (arm64 builds may legitimately be missing).
        if module.meta_yml is None or not Path(module.meta_yml).exists():
            log.debug(f"No meta.yml for {module.component_name}; containers need rebuilding")
            return False
        if not read_meta_yml(Path(module.meta_yml)).get("containers"):
            log.debug(f"meta.yml for {module.component_name} has no containers section; containers need rebuilding")
            return False

        return True

    def get_bioconda_version(self, module: NFCoreComponent) -> list[str]:
        """
        Extract the bioconda version from a module
        """
        # Check whether file exists and load it
        bioconda_packages = []
        if module.environment_yml is not None and module.environment_yml.exists():
            with open(module.environment_yml) as fh:
                env_yml = yaml.safe_load(fh)
            bioconda_packages = env_yml.get("dependencies", [])
        else:
            log.error(f"Could not read `environment.yml` of {module.component_name} module.")

        return bioconda_packages

    def _print_results(self) -> None:
        """
        Print the results for the bump_versions command
        Uses the ``rich`` library to print a set of formatted tables to the command line
        summarising the linting results.
        """

        log.debug("Printing bump_versions results")

        console = Console(force_terminal=rich_force_colors())
        # Find maximum module name length
        max_mod_name_len = 40
        for m in [self.up_to_date, self.updated, self.failed]:
            with contextlib.suppress(Exception):
                max_mod_name_len = max(len(m[2]), max_mod_name_len)

        def format_result(module_updates: list[tuple[str, str]], table: Table) -> Table:
            """
            Create rows for module updates
            """
            # TODO: Row styles don't work current as table-level style overrides.
            # I'd like to make an issue about this on the rich repo so leaving here in case there is a future fix
            last_modname = ""
            row_style = None
            for module_update in module_updates:
                if last_modname and module_update[1] != last_modname:
                    row_style = None if row_style else "magenta"
                last_modname = module_update[1]
                table.add_row(
                    Markdown(f"{module_update[1]}"),
                    Markdown(f"{module_update[0]}"),
                    style=row_style,
                )
            return table

        # Table of up to date modules
        if len(self.up_to_date) > 0 and self.show_up_to_date:
            console.print(
                Panel(
                    rf"[!] {len(self.up_to_date)} Module{_s(self.up_to_date)} version{_s(self.up_to_date)} up to date.",
                    style="bold green",
                )
            )
            table = Table(style="green", box=ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update Message")
            table = format_result(self.up_to_date, table)
            console.print(table)

        # Table of updated modules
        if len(self.updated) > 0:
            console.print(Panel(rf"[!] {len(self.updated)} Module{_s(self.updated)} updated", style="bold yellow"))
            table = Table(style="yellow", box=ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update message")
            table = format_result(self.updated, table)
            console.print(table)

        # Table of modules that couldn't be updated
        if len(self.failed) > 0:
            console.print(Panel(rf"[!] {len(self.failed)} Module update{_s(self.failed)} failed", style="bold red"))
            table = Table(style="red", box=ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update message")
            table = format_result(self.failed, table)
            console.print(table)

        # Table of modules ignored due to `.nf-core.yml`
        if len(self.ignored) > 0:
            console.print(Panel(rf"[!] {len(self.ignored)} Module update{_s(self.ignored)} ignored", style="grey58"))
            table = Table(style="grey58", box=ROUNDED)
            table.add_column("Module name", width=max_mod_name_len)
            table.add_column("Update message")
            table = format_result(self.ignored, table)
            console.print(table)
