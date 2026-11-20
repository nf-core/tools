# Lazy on Python 3.15+ (PEP 810), see scripts/update_lazy_modules.py
__lazy_modules__ = ["nf_core.utils"]

from nf_core.utils import lazy_attrs

# Lazy imports to keep CLI start-up fast
__getattr__, __dir__ = lazy_attrs(
    globals(),
    {
        "PipelineCreateApp": "nf_core.pipelines.create",
    },
)
