import sys

from click.shell_completion import CompletionItem

from nf_core.pipelines.list import Workflows


def autocomplete_pipelines(ctx, param, incomplete: str):
    try:
        wfs = Workflows()
        wfs.get_remote_workflows()
        wfs.get_local_nf_workflows()
        local_workflows = [wf.full_name for wf in wfs.local_workflows]
        remote_workflows = [wf.full_name for wf in wfs.remote_workflows]
        available_workflows = local_workflows + remote_workflows

        matches = [CompletionItem(wor) for wor in available_workflows if wor.startswith(incomplete)]

        return matches
    except Exception as e:
        print(f"[ERROR] Autocomplete failed: {e}", file=sys.stderr)
        return []
