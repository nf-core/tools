from nf_core.utils import lazy_attrs

# Lazy imports to keep CLI start-up fast
__getattr__, __dir__ = lazy_attrs(
    globals(),
    {
        "SubworkflowCreate": "nf_core.subworkflows.create",
        "SubworkflowInfo": "nf_core.subworkflows.info",
        "SubworkflowInstall": "nf_core.subworkflows.install",
        "SubworkflowLint": "nf_core.subworkflows.lint",
        "SubworkflowList": "nf_core.subworkflows.list",
        "SubworkflowPatch": "nf_core.subworkflows.patch",
        "SubworkflowRemove": "nf_core.subworkflows.remove",
        "SubworkflowUpdate": "nf_core.subworkflows.update",
    },
)
