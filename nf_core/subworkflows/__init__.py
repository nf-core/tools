import importlib

# Lazy imports to keep CLI start-up fast
_submodules = {
    "SubworkflowCreate": ".create",
    "SubworkflowInfo": ".info",
    "SubworkflowInstall": ".install",
    "SubworkflowLint": ".lint",
    "SubworkflowList": ".list",
    "SubworkflowPatch": ".patch",
    "SubworkflowRemove": ".remove",
    "SubworkflowUpdate": ".update",
}


def __getattr__(name):
    if name in _submodules:
        module = importlib.import_module(_submodules[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
