import logging
from pathlib import Path

import git

from nf_core.pipelines.containers_utils import ContainerConfigs

log = logging.getLogger(__name__)


def container_configs(self):
    """Check that the container configuration files in ``conf/`` are up to date.

    Runs ``nextflow inspect`` to regenerate container configuration files directly
    in ``conf/`` and uses ``git diff`` to detect changes.  If not in ``--fix`` mode
    the working tree is restored to its original state afterwards.

    Can be skipped by adding the following to the ``.nf-core.yml`` file:

    .. code-block:: yaml

        lint:
            container_configs: False
    """
    passed = []
    failed = []
    warned = []
    fixed = []
    could_fix = False

    conf_dir = Path(self.wf_path) / "conf"
    repo = git.Repo(self.wf_path)

    try:
        generated = ContainerConfigs(self.wf_path).generate_container_configs()
    except UserWarning as e:
        warned.append(f"Could not generate container configuration files: {e}")
        return {"passed": passed, "failed": failed, "warned": warned}

    # Files modified in the working tree (tracked and changed by generation)
    modified = {
        Path(d.a_path).name
        for d in repo.index.diff(None)
        if d.a_path and Path(d.a_path).parent.name == "conf" and Path(d.a_path).name.startswith("containers_")
    }
    # Newly created files (generated but not previously tracked)
    new = {
        Path(f).name
        for f in repo.untracked_files
        if Path(f).parent.name == "conf" and Path(f).name.startswith("containers_")
    }
    # Already-correct files: generated, tracked, and unchanged
    correct = generated - modified - new

    fixing = "container_configs" in self.fix

    for name in sorted(correct):
        passed.append(f"`conf/{name}` is up to date")

    for name in sorted(modified | new):
        if fixing:
            passed.append(f"`conf/{name}` is up to date")
            fixed.append(f"`conf/{name}` overwritten with regenerated container configuration.")
        else:
            if name in new:
                failed.append(f"`conf/{name}` is missing – please regenerate the container configuration files.")
            else:
                failed.append(f"`conf/{name}` is out of date – please regenerate the container configuration files.")
            could_fix = True

    if not fixing:
        # Restore working tree: reset modified tracked files and delete new untracked ones
        for name in modified:
            repo.git.restore(str(conf_dir / name))
        for name in new:
            (conf_dir / name).unlink(missing_ok=True)

    return {"passed": passed, "failed": failed, "warned": warned, "fixed": fixed, "could_fix": could_fix}
