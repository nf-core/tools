import logging
import re
from pathlib import Path
from typing import Dict, List

log = logging.getLogger(__name__)


class LintConfig:
    def __init__(self, wf_path: str, lint_config: Dict[str, List[str]]):
        self.wf_path = wf_path
        self.lint_config = lint_config

    def lint_file(self, lint_name: str, file_path: Path) -> Dict[str, List[str]]:
        """Lint a file and add the result to the passed or failed list."""

        fn = Path(self.wf_path, file_path)
        passed: List[str] = []
        failed: List[str] = []
        ignored: List[str] = []

        ignore_configs = self.lint_config.get(lint_name, [])

        # Return a failed status if we can't find the file
        if not fn.is_file():
            if ignore_configs:
                return {"ignored": [f"`{file_path}` not found, but it is ignored."]}
            else:
                return {"failed": [f"`${file_path}` not found"]}

        try:
            with open(fn) as fh:
                config = fh.read()
        except Exception as e:
            return {"failed": [f"Could not parse file: {fn}, {e}"]}

        # find sections with a withName: prefix
        sections = re.findall(r"['\"](.*)['\"]", config)

        # find all .nf files in the workflow directory
        nf_files = list(Path(self.wf_path).rglob("*.nf"))
        log.debug(f"found nf_files: {nf_files}")

        # check if withName sections are present in config, but not in workflow files
        for section in sections:
            if section not in ignore_configs or section.lower() not in ignore_configs:
                if not any(section in nf_file.read_text() for nf_file in nf_files):
                    failed.append(
                        f"`{file_path}` contains `withName:{section}`, but the corresponding process is not present in any of the following workflow files: `{nf_files}`."
                    )
                else:
                    passed.append(f"both `{file_path}` and `{[str(f) for f in nf_files]} contain `{section}`.")
            else:
                ignored.append(f"``{section}` is ignored")

        return {"passed": passed, "failed": failed, "ignored": ignored}


def modules_config(self) -> Dict[str, List[str]]:
    """Make sure the conf/modules.config file follows the nf-core template, especially removed sections.

    .. note:: You can choose to ignore this lint tests by editing the file called
        ``.nf-core.yml`` in the root of your pipeline and setting the test to false:

        .. code-block:: yaml

            lint:
                modules_config: False

        To disable this test only for specific modules, you can specify a list of module names.

        .. code-block:: yaml

            lint:
                modules_config:
                    - fastqc

    """

    result = LintConfig(self.wf_path, self.lint_config).lint_file("modules_config", Path("conf", "modules.config"))

    return result


def base_config(self) -> Dict[str, List[str]]:
    """Make sure the conf/base.config file follows the nf-core template, especially removed sections.

    .. note:: You can choose to ignore this lint tests by editing the file called
        ``.nf-core.yml`` in the root of your pipeline and setting the test to false:

        .. code-block:: yaml

            lint:
                base_config: False

    """

    result = LintConfig(self.wf_path, self.lint_config).lint_file("base_config", Path("conf", "base.config"))

    return result
