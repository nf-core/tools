from click.shell_completion import CompletionItem
from nf_core.modules.list import ModuleList
from nf_core.subworkflows.list import SubworkflowList
from nf_core.pipelines.list import Workflows


def autocomplete_components(ctx, param, incomplete: str, component_type: str, list_class):
    # Defaults
    modules_repo_url = "https://github.com/nf-core/modules"
    modules_repo_branch = "master"
    modules_repo_no_pull = False
    dir_folder = ctx.params.get("dir", ".")

    try:
        if ctx.obj is not None:
            modules_repo_url = ctx.obj.get("modules_repo_url", modules_repo_url)
            modules_repo_branch = ctx.obj.get("modules_repo_branch", modules_repo_branch)
            modules_repo_no_pull = ctx.obj.get("modules_repo_no_pull", modules_repo_no_pull)

        components_list = list_class(
            dir_folder, True, modules_repo_url, modules_repo_branch, modules_repo_no_pull
        )

        available_components = components_list.modules_repo.get_avail_components(component_type)

        return [
            CompletionItem(comp)
            for comp in available_components
            if comp.startswith(incomplete)
        ]
    except Exception as e:
        print(f"[ERROR] Autocomplete failed: {e}", file=sys.stderr)
        return []

def autocomplete_modules(ctx, param, incomplete: str):
    return autocomplete_components(ctx, param, incomplete, "modules", ModuleList)

def autocomplete_subworkflows(ctx, param, incomplete: str):
    return autocomplete_components(ctx, param, incomplete, "subworkflows", SubworkflowList)

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
