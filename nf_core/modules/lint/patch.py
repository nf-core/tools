from pathlib import Path

from ..modules_differ import ModulesDiffer
from ..nfcore_module import NFCoreModule


def patch(module_lint_obj, module: NFCoreModule):
    """
    Lint a patch file found in a module

    Checks that the file name is well formed, and that
    the patch can be applied in reverse with the correct result.
    """
    # Check if there exists a patch file
    patch_fn = f"{module.module_name.replace('/', '-')}.diff"
    patch_path = Path(module.module_dir, patch_fn)
    if not patch_path.exists():
        # Nothing to lint, just return
        return


def check_patch_valid(module_lint_obj, module: NFCoreModule, patch_path):
    with open(patch_path, "r") as fh:
        patch_lines = fh.readlines()

    # Check that the file contains a patch for at least one file
    # and that the file is in the correct directory
    paths_in_patch = []
    passed = True
    it = iter(patch_lines)
    try:
        while True:
            line = next(it)
            if line.startswith("---"):
                frompath = Path(line.split(" ")[1])
                line = next(it)
                if not line.startswith("+++"):
                    module.failed.append(
                        (
                            "patch_valid",
                            "Patch file invalid. Line starting with '---' should always be follow by line starting with '+++'",
                            patch_path,
                        )
                    )
                    passed = False
                topath = Path(line.split(" ")[1])
                if frompath == Path("/dev/null"):
                    paths_in_patch.append((frompath, ModulesDiffer.DiffEnum.CREATED))
                elif topath == Path("/dev/null"):
                    paths_in_patch.append((frompath, ModulesDiffer.DiffEnum.REMOVED))
                elif frompath == topath:
                    paths_in_patch.append((frompath, ModulesDiffer.DiffEnum.CHANGED))
                else:
                    module.failed.append(
                        (
                            "patch_valid",
                            "Patch file invaldi. From file '{frompath}' mismatched with to path '{topath}'",
                            patch_path,
                        )
                    )
                    passed = False
                # Check that the next line is hunk
                line = next(it)
                if not line.startswith("@@"):
                    module.failed.append(
                        (
                            "patch_valid",
                            "Patch file invalid. File declarations should be followed by hunk",
                            patch_path,
                        )
                    )
                    passed = False
    except StopIteration:
        pass

    if not passed:
        return False

    if len(paths_in_patch) == 0:
        module.failed.append(("patch_valid", "Patch file invalid. Found no patches", patch_path))
        return False

    # Go through the files and check that they exist
    # Warn about any created or removed files
    passed = True
    for path, diff_status in paths_in_patch:
        if diff_status == ModulesDiffer.DiffEnum.CHANGED:
            if not Path(module.base_dir, path).exists():
                module.failed.append(
                    (
                        "patch_valid",
                        f"Patch file invalid. Path '{path}' does not exist but is reported in patch file.",
                        patch_path,
                    )
                )
                passed = False
                continue
        elif diff_status == ModulesDiffer.DiffEnum.CREATED:
            if not Path(module.base_dir, path).exists():
                module.failed.append(
                    (
                        "patch_valid",
                        f"Patch file invalid. Path '{path}' does not exist but is reported in patch file.",
                        patch_path,
                    )
                )
                passed = False
                continue
            module.warned.append(
                ("patch", f"Patch file performs file creation of {path}. This is discouraged."), patch_path
            )
        elif diff_status == ModulesDiffer.DiffEnum.REMOVED:
            if Path(module.base_dir, path).exists():
                module.failed.append(
                    (
                        "patch_valid",
                        f"Patch file invalid. Path '{path}' is reported as deleted but exists.",
                        patch_path,
                    )
                )
                passed = False
                continue
            module.warned.append(
                ("patch", f"Patch file performs file deletion of {path}. This is discouraged.", patch_path)
            )
        if passed:
            module.passed(("patch_valid", "Patch file is valid", patch_path))
        return passed
