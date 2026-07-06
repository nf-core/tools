import importlib

# Lazy imports to keep CLI start-up fast
_submodules = {
    "PipelineCreateApp": ".create",
}


def __getattr__(name):
    if name in _submodules:
        module = importlib.import_module(_submodules[name], __name__)
        globals()[name] = getattr(module, name)
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
