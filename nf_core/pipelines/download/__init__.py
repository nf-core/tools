# Lazy on Python 3.15+ (PEP 810), see scripts/update_lazy_modules.py
__lazy_modules__ = ["nf_core.pipelines.download.download"]

from .download import DownloadWorkflow
