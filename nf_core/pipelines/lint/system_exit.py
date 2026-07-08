import logging
from pathlib import Path

from nf_core import astgrep

log = logging.getLogger(__name__)

RULE_FILE = Path(__file__).parent / "rules" / "system_exit.yml"


def system_exit(self):
    """Check for System.exit calls in groovy/nextflow code

    Calls to System.exit(1) should be replaced by throwing errors

    This lint test looks for all calls to `System.exit`
    in any file with the `.nf` or `.groovy` extension

    The match logic lives in the ast-grep rule file ``rules/system_exit.yml``.
    See ``nf_core.astgrep.find_matches`` for the structural vs regex-fallback behaviour.
    """
    root_dir = Path(self.wf_path)
    files = list(root_dir.rglob("*.nf")) + list(root_dir.rglob("*.groovy"))

    rule = astgrep.load_rule(RULE_FILE)
    warned = [
        f"{rule['message']} in {file.name}: _{text}_  [line {line_num}]"
        for file, line_num, text in astgrep.find_matches(rule, files)
    ]
    passed = [] if warned else ["No `System.exit` calls found"]

    return {"passed": passed, "warned": warned}
