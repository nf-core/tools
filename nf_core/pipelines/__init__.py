def __getattr__(name):
    # Lazy import to keep CLI start-up fast
    if name == "PipelineCreateApp":
        from .create import PipelineCreateApp

        return PipelineCreateApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
