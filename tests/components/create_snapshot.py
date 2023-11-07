import os
from pathlib import Path

from nf_core.components.snapshot_generator import ComponentTestSnapshotGenerator

from ..utils import GITLAB_NFTEST_BRANCH, GITLAB_URL


def test_generate_snapshot_module(self):
    """Generate the snapshot for a module in nf-core/modules clone"""
    os.chdir(self.nfcore_modules)
    snap_generator = ComponentTestSnapshotGenerator(
        component_type="modules",
        component_name="fastqc",
        no_prompts=True,
        remote_url=GITLAB_URL,
        branch=GITLAB_NFTEST_BRANCH,
    )
    try:
        snap_generator.run()
    except UserWarning as e:
        assert False, f"'ComponentTestSnapshotGenerator' raised an exception {e}"

    assert Path("modules", "nf-core-test", "fastqc", "tests", "main.nf.test.snap").exists()


def test_update_snapshot_module(self):
    """Update the snapshot of a module in nf-core/modules clone"""
    os.chdir(self.nfcore_modules)
    snap_generator = ComponentTestSnapshotGenerator(
        component_type="modules",
        component_name="bwa/mem",
        no_prompts=True,
        remote_url=GITLAB_URL,
        branch=GITLAB_NFTEST_BRANCH,
        update=True,
    )
    try:
        snap_generator.run()
    except UserWarning as e:
        assert False, f"'ComponentTestSnapshotGenerator' raised an exception {e}"

    assert Path("modules", "nf-core-test", "bwa", "mem", "tests", "main.nf.test.snap").exists()
