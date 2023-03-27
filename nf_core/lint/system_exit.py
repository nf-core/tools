import logging
from pathlib import Path

log = logging.getLogger(__name__)


def system_exit(self):
    passed = []
    warned = []

    root_dir = Path(self.wf_path)

    # Get all groovy and nf files
    groovy_files = [f for f in root_dir.rglob("*.groovy")]
    nf_files = [f for f in root_dir.rglob("*.nf")]
    to_check = nf_files + groovy_files

    for file in to_check:
        with file.open() as fh:
            for l in fh.readlines():
                if "System.exit" in l:
                    warned.append(f"`System.exit` in {file.name}: _{l.strip()}_")
    if len(warned) == 0:
        passed.append("No `System.exit` calls found")

    return {"passed": passed, "warned": warned}
