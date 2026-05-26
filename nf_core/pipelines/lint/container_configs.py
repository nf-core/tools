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

    # Snapshot the content of existing container config files before generation
    snapshot: dict[str, str] = {}
    for path in conf_dir.glob("containers_*"):
        snapshot[path.name] = path.read_text()

    try:
        generated = ContainerConfigs(self.wf_path).generate_container_configs()
    except UserWarning as e:
        warned.append(f"Could not generate container configuration files: {e}")
        return {"passed": passed, "failed": failed, "warned": warned}

    log.debug(f"Generated {len(generated)} container config file(s): {', '.join(sorted(generated)) or 'none'}")

    # Compare generated content to pre-generation snapshot
    modified: set[str] = set()
    new: set[str] = set()
    correct: set[str] = set()

    for name in generated:
        new_content = (conf_dir / name).read_text() if (conf_dir / name).exists() else ""
        old_content = snapshot.get(name)
        if old_content is None:
            new.add(name)
        elif new_content != old_content:
            modified.add(name)
        else:
            correct.add(name)

    log.debug(f"Container config status — correct: {len(correct)}, modified: {len(modified)}, new: {len(new)}")

    fixing = "container_configs" in self.fix

    for name in sorted(correct):
        passed.append(f"`conf/{name}` is up to date")

    for name in sorted(modified | new):
        if fixing:
            log.debug(f"Overwriting `conf/{name}` with regenerated container configuration")
            passed.append(f"`conf/{name}` is up to date")
            fixed.append(f"`conf/{name}` overwritten with regenerated container configuration.")
        else:
            if name in new:
                failed.append(f"`conf/{name}` is missing – please regenerate the container configuration files.")
            else:
                failed.append(f"`conf/{name}` is out of date – please regenerate the container configuration files.")
            could_fix = True

    if not fixing:
        # Restore working tree: write back original content for modified files, remove new files
        log.debug(f"Restoring working tree: resetting {len(modified)} modified, removing {len(new)} new file(s)")
        for name in modified:
            (conf_dir / name).write_text(snapshot[name])
        for name in new:
            (conf_dir / name).unlink(missing_ok=True)

    return {"passed": passed, "failed": failed, "warned": warned, "fixed": fixed, "could_fix": could_fix}
