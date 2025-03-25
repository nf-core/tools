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
    metadata_file = Path(self.wf_path, "ro-crate-metadata.json")
    readme_file = Path(self.wf_path, "README.md")

    # Only proceed if both files exist
    if not (metadata_file.exists() and readme_file.exists()):
        if not metadata_file.exists():
            failed.append("ro-crate-metadata.json not found")
        if not readme_file.exists():
            failed.append("README.md not found")
        return {"passed": passed, "warned": warned, "failed": failed}

    try:
        metadata_content = metadata_file.read_text(encoding="utf-8")
        metadata_dict = json.loads(metadata_content)
    except json.JSONDecodeError as e:
        log.error("Failed to decode JSON from ro-crate-metadata.json: %s", e)
        failed.append("Invalid JSON in ro-crate-metadata.json")
        return {"passed": passed, "warned": warned, "failed": failed}

    # Use safe fallback in case description is None
    rc_description_graph = metadata_dict.get("@graph", [{}])[0].get("description") or ""

    readme_content = readme_file.read_text(encoding="utf-8")

    # Compare the two strings and add a linting error if they don't match
    if readme_content != rc_description_graph:
        # If the --fix flag is set, you could overwrite the RO-Crate description with the README content:
        if self.fix:
            metadata_dict.get("@graph")[0]["description"] = readme_content
            with metadata_file.open("w", encoding="utf-8") as f:
                json.dump(metadata_dict, f, indent=4)
            passed.append("Mismatch fixed: RO-Crate description updated from README.md.")
        else:
            failed.append("The RO-Crate descriptions do not match the README.md content.")
            raise AssertionError(
                "The RO-Crate descriptions do not match the README.md content. "
                "You can fix this by running `nf-core lint --fix`."
            )
    else:
        passed.append("RO-Crate descriptions are in sync with README.md.")
    return {"passed": passed, "warned": warned, "failed": failed}
