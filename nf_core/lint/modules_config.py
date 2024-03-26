from pathlib import Path
from typing import Dict, List

from nf_core.lint_utils import LintFile


def modules_config(self) -> Dict[str, List[str]]:
    """Make sure the conf/modules.config file follows the nf-core template, especially removed sections."""

    result = LintFile(self.wf_path, self.lint_config).lint_file(
        "modules_config", Path("conf", "modules.config"), ["withName:CUSTOM_DUMPSOFTWAREVERSIONS"]
    )

    return result
