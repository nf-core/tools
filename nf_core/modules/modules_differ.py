import difflib
import enum
import json
import logging
import os
import re
import shutil
import tempfile
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

import nf_core.utils
from nf_core.utils import plural_s

log = logging.getLogger(__name__)


class ModulesDiffer:
    """
    Static class that provides functionality for computing diffs between
    different instances of a module
    """

    class DiffEnum(enum.Enum):
        """
        Enumeration for keeping track of
        the diff status of a pair of files
        """

        UNCHANGED = enum.auto()
        CHANGED = enum.auto()
        CREATED = enum.auto()
        REMOVED = enum.auto()

    @staticmethod
    def get_module_diffs(from_dir, to_dir, for_git=True, dsp_from_dir=None, dsp_to_dir=None):
        """
        Compute the diff between the current module version
        and the new version.

        Args:
            from_dir (strOrPath): The folder containing the old module files
            to_dir (strOrPath): The folder containing the new module files
            path_in_diff (strOrPath): The directory displayed containing the module
                                      file in the diff. Added so that temporary dirs
                                      are not shown
            for_git (bool): indicates whether the diff file is to be
                            compatible with `git apply`. If true it
                            adds a/ and b/ prefixes to the file paths
            dsp_from_dir (str | Path): The from directory to display in the diff
            dsp_to_dir (str | Path): The to directory to display in the diff

        Returns:
            dict[str, (ModulesDiffer.DiffEnum, str)]: A dictionary containing
            the diff type and the diff string (empty if no diff)
        """
        if dsp_from_dir is None:
            dsp_from_dir = from_dir
        if dsp_to_dir is None:
            dsp_to_dir = to_dir
        if for_git:
            dsp_from_dir = Path("a", dsp_from_dir)
            dsp_to_dir = Path("b", dsp_to_dir)

        diffs = {}
        # Get all unique filenames in the two folders.
        # `dict.fromkeys()` is used instead of `set()` to preserve order
        files = dict.fromkeys(os.listdir(to_dir))
        files.update(dict.fromkeys(os.listdir(from_dir)))
        files = list(files)

        # Loop through all the module files and compute their diffs if needed
        for file in files:
            temp_path = Path(to_dir, file)
            curr_path = Path(from_dir, file)
            if temp_path.exists() and curr_path.exists() and temp_path.is_file():
                with open(temp_path, "r") as fh:
                    new_lines = fh.readlines()
                with open(curr_path, "r") as fh:
                    old_lines = fh.readlines()

                if new_lines == old_lines:
                    # The files are identical
                    diffs[file] = (ModulesDiffer.DiffEnum.UNCHANGED, ())
                else:
                    # Compute the diff
                    diff = difflib.unified_diff(
                        old_lines,
                        new_lines,
                        fromfile=str(Path(dsp_from_dir, file)),
                        tofile=str(Path(dsp_to_dir, file)),
                    )
                    diffs[file] = (ModulesDiffer.DiffEnum.CHANGED, diff)

            elif temp_path.exists():
                with open(temp_path, "r") as fh:
                    new_lines = fh.readlines()
                # The file was created
                # Show file against /dev/null
                diff = difflib.unified_diff(
                    [],
                    new_lines,
                    fromfile=str(Path("/dev", "null")),
                    tofile=str(Path(dsp_to_dir, file)),
                )
                diffs[file] = (ModulesDiffer.DiffEnum.CREATED, diff)

            elif curr_path.exists():
                # The file was removed
                # Show file against /dev/null
                with open(curr_path, "r") as fh:
                    old_lines = fh.readlines()
                diff = difflib.unified_diff(
                    old_lines,
                    [],
                    fromfile=str(Path(dsp_from_dir, file)),
                    tofile=str(Path("/dev", "null")),
                )
                diffs[file] = (ModulesDiffer.DiffEnum.REMOVED, diff)

        return diffs

    @staticmethod
    def write_diff_file(
        diff_path,
        module,
        repo_name,
        from_dir,
        to_dir,
        current_version,
        new_version,
        file_action="a",
        for_git=True,
        dsp_from_dir=None,
        dsp_to_dir=None,
    ):
        """
        Writes the diffs of a module to the diff file.

        Args:
            diff_path (str | Path): The path to the file that should be appended
            module (str): The module name
            repo_name (str): The name of the repo where the module resides
            from_dir (str | Path): The directory containing the old module files
            to_dir (str | Path): The directory containing the new module files
            diffs (dict[str, (ModulesDiffer.DiffEnum, str)]): A dictionary containing
                                                              the type of change and
                                                              the diff (if any)
            module_dir (str | Path): The path to the current installation of the module
            current_version (str): The installed version of the module
            new_version (str): The version of the module the diff is computed against
            for_git (bool): indicates whether the diff file is to be
                            compatible with `git apply`. If true it
                            adds a/ and b/ prefixes to the file paths
            dsp_from_dir (str | Path): The from directory to display in the diff
            dsp_to_dir (str | Path): The to directory to display in the diff
        """

        diffs = ModulesDiffer.get_module_diffs(from_dir, to_dir, for_git, dsp_from_dir, dsp_to_dir)
        log.info(f"Writing diff of '{module}' to '{diff_path}'")
        with open(diff_path, file_action) as fh:
            if current_version is not None and new_version is not None:
                fh.write(
                    f"Changes in module '{Path(repo_name, module)}' between"
                    f" ({current_version}) and"
                    f" ({new_version})\n"
                )
            else:
                fh.write(f"Changes in module '{Path(repo_name, module)}'\n")

            for file, (diff_status, diff) in diffs.items():
                if diff_status != ModulesDiffer.DiffEnum.UNCHANGED:
                    # The file has changed
                    # fh.write(f"Changes in '{Path(from_dir, file)}':\n")
                    # Write the diff lines to the file
                    for line in diff:
                        fh.write(line)
                    fh.write("\n")

            fh.write("*" * 60 + "\n")

    @staticmethod
    def append_modules_json_diff(diff_path, old_modules_json, new_modules_json, modules_json_path, for_git=True):
        """
        Compare the new modules.json and builds a diff

        Args:
            diff_fn (str): The diff file to be appended
            old_modules_json (nested dict): The old modules.json
            new_modules_json (nested dict): The new modules.json
            modules_json_path (str): The path to the modules.json
            for_git (bool): indicates whether the diff file is to be
                            compatible with `git apply`. If true it
                            adds a/ and b/ prefixes to the file paths
        """
        fromfile = modules_json_path
        tofile = modules_json_path
        if for_git:
            fromfile = Path("a", fromfile)
            tofile = Path("b", tofile)

        modules_json_diff = difflib.unified_diff(
            json.dumps(old_modules_json, indent=4).splitlines(keepends=True),
            json.dumps(new_modules_json, indent=4).splitlines(keepends=True),
            fromfile=str(fromfile),
            tofile=str(tofile),
        )

        # Save diff for modules.json to file
        with open(diff_path, "a") as fh:
            fh.write("Changes in './modules.json'\n")
            for line in modules_json_diff:
                fh.write(line)
            fh.write("*" * 60 + "\n")

    @staticmethod
    def print_diff(module, repo_name, from_dir, to_dir, current_version, new_version):
        """
        Prints the diffs between two module versions to the terminal

        Args:
            module (str): The module name
            repo_name (str): The name of the repo where the module resides
            diffs (dict[str, (ModulesDiffer.DiffEnum, str)]): A dictionary containing
            the type of change and the diff (if any)
            from_dir (str): The directory containing the old module files
            to_dir (str): The directory containing the new module files
            module_dir (str): The path to the current installation of the module
            current_version (str): The installed version of the module
            new_version (str): The version of the module the diff is computed against
        """
        diffs = ModulesDiffer.get_module_diffs(from_dir, to_dir)
        console = Console(force_terminal=nf_core.utils.rich_force_colors())
        if current_version is not None and new_version is not None:
            log.info(
                f"Changes in module '{Path(repo_name, module)}' between" f" ({current_version}) and" f" ({new_version})"
            )
        else:
            log.info(f"Changes in module '{Path(repo_name, module)}'")

        for file, (diff_status, diff) in diffs.items():
            if diff_status == ModulesDiffer.DiffEnum.UNCHANGED:
                # The files are identical
                log.info(f"'{Path(from_dir, file)}' is unchanged")
            elif diff_status == ModulesDiffer.DiffEnum.CREATED:
                # The file was created between the commits
                log.info(f"'{Path(from_dir, file)}' was created")
            elif diff_status == ModulesDiffer.DiffEnum.REMOVED:
                # The file was removed between the commits
                log.info(f"'{Path(from_dir, file)}' was removed")
            else:
                # The file has changed
                log.info(f"Changes in '{Path(module, file)}':")
                # Pretty print the diff using the pygments diff lexer
                console.print(Syntax("".join(diff), "diff", theme="ansi_light"))
