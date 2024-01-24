#!/usr/bin/env python
""" Code to deal with pipeline RO (Research Object) Crates """


import logging
import sys
import tempfile
from pathlib import Path
from typing import Union

import requests
import rocrate.model.entity
import rocrate.rocrate
from rocrate.model.person import Person

from nf_core.utils import Pipeline

log = logging.getLogger(__name__)


class RoCrate:
    """Class to generate an RO Crate for a pipeline"""

    def __init__(self, pipeline_dir: Path, version=""):
        from nf_core.utils import is_pipeline_directory

        try:
            is_pipeline_directory(pipeline_dir)
        except UserWarning as e:
            log.error(e)
            sys.exit(1)

        self.pipeline_dir = pipeline_dir
        self.version = version
        self.crate: rocrate.rocrate.ROCrate
        self.pipeline_obj = Pipeline(str(self.pipeline_dir))
        self.pipeline_obj._load()

    def create_ro_crate(self, outdir: Path, metadata_fn="", zip_fn=""):
        """Create an RO Crate for the pipeline"""

        # Set input paths
        self.get_crate_paths(outdir)

        self.make_workflow_ro_crate(self.pipeline_dir)

        # Save just the JSON metadata file
        if metadata_fn is not None:
            log.info(f"Saving metadata file '{metadata_fn}'")
            # Save the crate to a temporary directory
            tmpdir = Path(tempfile.mkdtemp(), "wf")
            self.crate.write(tmpdir)
            # Now save just the JSON file
            crate_json_fn = Path(tmpdir, "ro-crate-metadata.json")
            crate_json_fn.rename(metadata_fn)

        # Save the whole crate zip file
        if zip_fn is not None:
            log.info(f"Saving zip file '{zip_fn}'")
            self.crate.write_zip(zip_fn)

    def make_workflow_ro_crate(self, path: Path):
        import nf_core.utils

        if self.pipeline_obj is None:
            raise ValueError("Pipeline object not loaded")

        # Create the RO Crate
        self.crate = rocrate.rocrate.ROCrate()

        # Conform to RO-Crate 1.1 and workflowhub-ro-crate

        # Set language type
        programming_language = rocrate.model.entity.Entity(
            self.crate,
            "#nextflow",
            properties={
                "@type": ["ComputerLanguage", "SoftwareApplication"],
                "name": "Nextflow",
                "url": "https://www.nextflow.io/",
                "identifier": "https://www.nextflow.io/",
                "version": self.pipeline_obj.nf_config.get("manifest.nextflowVersion", ""),
            },
        )
        self.crate.add(programming_language)
        self.crate.update_jsonld(
            {
                "@id": "ro-crate-metadata.json",
                "conformsTo": [
                    {"@id": "https://w3id.org/ro/crate/1.1"},
                    {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
                ],
            }
        )

        # Set main entity file
        wf_file = self.crate.add_jsonld(
            {
                "@id": "main.nf",
                "@type": ["File", "SoftwareSourceCode", "ComputationalWorkflow"],
            },
        )
        self.crate.mainEntity = wf_file
        # self.crate.update_jsonld({"@id": "main.nf", "@type": ["File", "SoftwareSourceCode", "ComputationalWorkflow"]})

        self.add_authors(wf_file)
        wf_file.append_to("programmingLanguage", programming_language)

        # add readme as description
        readme = Path(self.pipeline_dir, "README.md")
        self.crate.description = readme.read_text()

        self.crate.license = "MIT"

        # add doi as identifier
        # self.crate.identifier = self.pipeline_obj.get("manifest", {}).get("doi", "")
        self.crate.name = f'Research Object Crate for {self.pipeline_obj.nf_config.get("manifest.name")}'

        if "dev" in self.pipeline_obj.nf_config.get("manifest.version", ""):
            self.crate.CreativeWorkStatus = "InProgress"
        else:
            self.crate.CreativeWorkStatus = "Stable"

        # Add all other files
        wf_filenames = nf_core.utils.get_wf_files(self.pipeline_dir)
        log.debug(f"Adding {len(wf_filenames)} workflow files")
        for fn in wf_filenames:
            # check if it wasn't already added
            if fn == "main.nf":
                continue
            # add nextflow language to .nf and .config files
            if fn.endswith(".nf") or fn.endswith(".config"):
                log.debug(f"Adding workflow file: {fn}")
                self.crate.add_file(fn, properties={"programmingLanguage": {"@id": "#nextflow"}})
            if fn.endswith(".png"):
                log.debug(f"Adding workflow file: {fn}")
                self.crate.add_file(fn, properties={"@type": ["File", "ImageObject"]})
                if "metro_map" in fn:
                    log.info(f"Setting main entity image to: {fn}")
                    wf_file.append_to("image", {"@id": fn})
            if fn.endswith(".md"):
                log.debug(f"Adding workflow file: {fn}")
                self.crate.add_file(fn, properties={"encodingFormat": "text/markdown"})
            else:
                log.debug(f"Adding workflow file: {fn}")
                self.crate.add_file(fn)

        # get keywords from github topics
        remote_workflows = requests.get("https://nf-co.re/pipelines.json").json()["remote_workflows"]
        # go through all remote workflows and find the one that matches the pipeline name
        topics = ["nf-core", "nextflow"]
        for remote_wf in remote_workflows:
            if remote_wf["name"] == self.pipeline_obj.pipeline_name.replace("nf-core/", ""):
                topics = topics + remote_wf["topics"]
                break

        log.debug(f"Adding topics: {topics}")
        wf_file.append_to("keywords", topics)

    def add_authors(self, wf_file):
        """
        Add workflow authors to the crate
        NB: We don't have much metadata here - scope to improve in the future
        """
        # add author entity to crate

        try:
            authors = self.pipeline_obj.nf_config["manifest.author"].split(",")
        except KeyError:
            log.error("No author field found in manifest of nextflow.config")
            return
        for author in authors:
            log.debug(f"Adding author: {author}")
            orcid = get_orcid(author)
            author_entitity = self.crate.add(Person(self.crate, orcid, properties={"name": author}))
            wf_file.append_to("author", author_entitity)

    def get_crate_paths(self, path):
        """Given a pipeline name, directory, or path, set wf_crate_filename"""

        path = Path(path)

        if path.is_dir():
            self.pipeline_dir = path
            # wf_crate_filename = path / "ro-crate-metadata.json"
        elif path.is_file():
            self.pipeline_dir = path.parent
            # wf_crate_filename = path

        # Check that the schema file exists
        if self.pipeline_dir is None:
            raise OSError(f"Could not find pipeline '{path}'")


def get_orcid(name: str) -> Union[str, None]:
    base_url = "https://pub.orcid.org/v3.0/search/"
    headers = {
        "Accept": "application/json",
    }
    params = {"q": f'family-name:"{name.split()[-1]}" AND given-names:"{name.split()[0]}"'}
    response = requests.get(base_url, params=params, headers=headers)

    if response.status_code == 200:
        json_response = response.json()
        if json_response.get("num-found") == 1:
            orcid_uri = json_response.get("result")[0].get("orcid-identifier", {}).get("uri")
            log.info(f"Using found ORCID for {name}. Please double-check: {orcid_uri}")
            return orcid_uri
        else:
            log.debug(f"No exact ORCID found for {name}. See {response.url}")
            return None
    else:
        return f"API request unsuccessful. Status code: {response.status_code}"
