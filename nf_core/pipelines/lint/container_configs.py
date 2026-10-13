import logging
from pathlib import Path

from nf_core.pipelines.containers_utils import ContainerConfigs

log = logging.getLogger(__name__)


def container_configs(self):
    """Check that the container configuration files in ``conf/`` are up to date.

    Scans all ``meta.yml`` files under ``modules/`` that contain a ``containers``
    key, reads the process name from the sibling ``main.nf``, and regenerates
    the container configuration files in ``conf/``.  Uses direct content comparison
    to detect changes.  If not in ``--fix`` mode the working tree is restored to its
    original state afterwards.

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

    def read_container_configs() -> dict[str, bytes]:
        return {path.name: path.read_bytes() for path in conf_dir.glob("containers_*")}

    before = read_container_configs()
    try:
        generated = ContainerConfigs(self.wf_path).generate_container_configs()
    except UserWarning as e:
        warned.append(f"Could not generate container configuration files: {e}")
        return {"passed": passed, "failed": failed, "warned": warned}
    after = read_container_configs()

    new = after.keys() - before.keys()
    removed = before.keys() - after.keys()
    modified = {name for name in before.keys() & after.keys() if before[name] != after[name]}
    correct = generated - new - modified

    log.debug(
        f"Container config status — correct: {len(correct)}, modified: {len(modified)}, "
        f"new: {len(new)}, removed: {len(removed)}"
    )

    fixing = "container_configs" in self.fix

    for name in sorted(correct):
        passed.append(f"`conf/{name}` is up to date")

    for name in sorted(new | modified | removed):
        if fixing:
            if name in removed:
                fixed.append(f"`conf/{name}` removed, as no module provides containers for it anymore.")
            else:
                passed.append(f"`conf/{name}` is up to date")
                fixed.append(f"`conf/{name}` overwritten with regenerated container configuration.")
        else:
            reason = "missing" if name in new else "obsolete" if name in removed else "out of date"
            failed.append(f"`conf/{name}` is {reason} – please regenerate the container configuration files.")

    if not fixing:
        could_fix = bool(new | modified | removed)
        # Restore working tree to its pre-generation state
        for name in modified | removed:
            (conf_dir / name).write_bytes(before[name])
        for name in new:
            (conf_dir / name).unlink()

    return {"passed": passed, "failed": failed, "warned": warned, "fixed": fixed, "could_fix": could_fix}
