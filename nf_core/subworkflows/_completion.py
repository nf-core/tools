import sys

from click.shell_completion import CompletionItem

from nf_core.subworkflows.list import SubworkflowList


def autocomplete_subworkflows(ctx, param, incomplete: str):
    # Provide fallback/defaults if ctx.obj is not available
    modules_repo_url = "https://github.com/nf-core/modules"
    modules_repo_branch = "master"
    modules_repo_no_pull = False

    try:
        if ctx.obj is not None:
            modules_repo_url = ctx.obj.get("modules_repo_url", modules_repo_url)
            modules_repo_branch = ctx.obj.get("modules_repo_branch", modules_repo_branch)
            modules_repo_no_pull = ctx.obj.get("modules_repo_no_pull", modules_repo_no_pull)

        subworkflow_list = SubworkflowList(
            ".",
            True,
            modules_repo_url,
            modules_repo_branch,
            modules_repo_no_pull,
        )

        available_subworkflows = subworkflow_list.modules_repo.get_avail_components("subworkflows")

        matches = [CompletionItem(sub) for sub in available_subworkflows if sub.startswith(incomplete)]

        return matches
    except Exception as e:
        print(f"[ERROR] Autocomplete failed: {e}", file=sys.stderr)
        return []
