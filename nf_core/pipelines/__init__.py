from nf_core.utils import lazy_attrs

# Lazy imports to keep CLI start-up fast
__getattr__, __dir__ = lazy_attrs(
    globals(),
    {
        "PipelineCreateApp": "nf_core.pipelines.create",
    },
)
