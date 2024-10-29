import logging
from pathlib import Path

log = logging.getLogger(__name__)


def local_component_structure(self):
    """
    Check that the local modules and subworkflows directories in a pipeline have the correct format:

    .. code-block:: bash

        modules/local/TOOL/SUBTOOL

    Prior to nf-core/tools release 3.1.0 the directory structure allowed top-level `*.nf` files:

    .. code-block:: bash

        modules/local/modules/TOOL_SUBTOOL.nf
    """
    warned = []
    for nf_file in Path(self.wf_path, "modules", "local").glob("*.nf"):
        warned.append(f"{nf_file.name} in modules/local should be moved to a TOOL/SUBTOOL/main.nf structure")
    for nf_file in Path(self.wf_path, "subworkflows", "local").glob("*.nf"):
        warned.append(f"{nf_file.name} in subworkflows/local should be moved to a SUBWORKFLOW_NAME/main.nf structure")

    # If there are modules installed in the wrong location
    passed = []
    if len(warned) == 0:
        passed = ["modules directory structure is correct 'modules/nf-core/TOOL/SUBTOOL'"]
    return {"passed": passed, "warned": warned, "failed": [], "ignored": []}
