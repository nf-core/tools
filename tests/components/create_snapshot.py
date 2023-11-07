import os
from pathlib import Path

from nf_core.components.snapshot_generator import ComponentTestSnapshotGenerator

from ..utils import GITLAB_NFTEST_BRANCH, GITLAB_URL


def test_generate_snapshot_module(self):
    """Generate the snapshot for a module in nf-core/modules clone"""
    for root, directories, files in os.walk(self.nfcore_modules):
        print(f"Directory: {root}")
        for file in files:
            print(f"  File: {file}")

    snap_generator = ComponentTestSnapshotGenerator(
        component_type="modules",
        component_name="fastqc",
        no_prompts=True,
        directory=self.nfcore_modules,
        remote_url=GITLAB_URL,
        branch=GITLAB_NFTEST_BRANCH,
    )
    assert snap_generator.run()

    assert os.path.exists(Path(self.nfcore_modules, "modules", "nf-core-test", "fastqc", "tests", "main.nf.test.snap"))


def test_update_snapshot_module(self):
    """Update the snapshot of a module in nf-core/modules clone"""
    snap_generator = ComponentTestSnapshotGenerator(
        component_type="modules",
        component_name="bwa/mem",
        no_prompts=True,
        update=True,
    )
    assert snap_generator.run()

    assert os.path.exists(
        Path(self.nfcore_modules, "modules", "nf-core-test", "bwa", "mem", "tests", "main.nf.test.snap")
    )
