import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def rocrate_readme_sync(self):
    """
    Check if the RO-Crate description in ro-crate-metadata.json matches the README.md content.
    If the --fix is set, the RO-Crate description will be updated to match the README.md content.
    """

    warned = []
    passed = []
    failed = []

    # Check if the file exists before trying to load it
    metadata_file = Path("ro-crate-metadata.json")
    readme_file = Path("README.md")

    if metadata_file.exists():
        # Load the metadata file
        with metadata_file.open("r", encoding="utf-8") as f:
            metadata_dict = json.load(f)
            rc_description_graph = metadata_dict.get("@graph")[0].get("description").strip()
    else:
        failed.append("ro-crate-metadata.json not found")

    if readme_file.exists():
        readme_content = readme_file.read_text(encoding="utf-8").strip()
    else:
        failed.append("README.md not found")

    # Compare the two strings and add a linting error if they don't match
    if readme_content != rc_description_graph:
        # If the --fix flag is set, you could overwrite the RO-Crate description with the README content:
        if self.fix:
            metadata_dict.get("@graph")[0]["description"] = readme_content
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, indent=4)
            passed.append("Mismatch fixed: RO-Crate description updated from README.md.")
        else:
            warned.append("The RO-Crate descriptions do not match the README.md content.")
    else:
        passed.append("RO-Crate descriptions are in sync with README.md.")
    return {"passed": passed, "warned": warned, "failed": failed}
