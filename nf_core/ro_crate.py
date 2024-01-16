#!/usr/bin/env python
""" Code to deal with pipeline RO (Research Object) Crates """


import logging
import tempfile
from pathlib import Path

import rocrate.model.entity
import rocrate.rocrate
from typing import Union

log = logging.getLogger(__name__)


class RoCrate:
    """Class to generate an RO Crate for a pipeline"""

    def __init__(self, pipeline_dir: Union[str, Path], version=""):
        self.pipeline_dir = pipeline_dir
        self.version = version

    def create_ro_create(self, outdir: Path, metadata_fn="", zip_fn=""):
        """Create an RO Crate for the pipeline"""

        # Create a temporary directory for the RO Crate
        rocrate_dir = tempfile.mkdtemp(prefix="nf-core-ro-crate-")

        # Create the RO Crate
        wf_crate = rocrate.rocrate.ROCrate(rocrate_dir)

        # Set main entity file
        wf_file = wf_crate.add_file(Path(self.pipeline_dir, "nextflow.config"), "nextflow.config")
        wf_crate.mainEntity = wf_file

        # Set language type
        programming_language = rocrate.model.entity.Entity(
            wf_crate,
            "https://www.nextflow.io/",
            properties={
                "@type": ["ComputerLanguage", "SoftwareApplication"],
                "name": "Nextflow",
                "url": "https://www.nextflow.io/",
            },
        )
        wf_crate.add(programming_language)
