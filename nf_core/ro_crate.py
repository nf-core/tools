#!/usr/bin/env python
""" Code to deal with pipeline RO (Research Object) Crates """

from __future__ import print_function

import logging
import os
import tempfile

import rocrate.rocrate
import rocrate.model.entity

import nf_core.list, nf_core.utils

log = logging.getLogger(__name__)


class RoCrate(object):
    """ Class to generate an RO Crate metadata file for a pipeline """

    def __init__(self):
        """ Initialise the object """

        self.crate = None
        self.schema_obj = None
        self.pipeline_dir = None
        wf_crate_filename = None

    def create_ro_crate(self, path, metadata_fn=None, zip_fn=None):

        # Set input paths
        self.get_crate_paths(path)

        # Make the ROCrate object
        self.crate = self.make_workflow_rocrate()

        # Save just the JSON metadata file
        if metadata_fn is not None:
            log.info("Saving metadata file '{}'".format(metadata_fn))
            # Save the crate to a temporary directory
            tmpdir = os.path.join(tempfile.mkdtemp(), "wf")
            self.crate.write_crate(tmpdir)
            # Now save just the JSON file
            crate_json_fn = os.path.join(tmpdir, "ro-crate-metadata.jsonld")
            os.replace(crate_json_fn, metadata_fn)

        # Save the whole crate zip file
        if zip_fn is not None:
            log.info("Saving zip file '{}'".format(zip_fn))
            self.crate.write_zip(zip_fn)

    def get_crate_paths(self, path):
        """ Given a pipeline name, directory, or path, set wf_crate_filename """

        if os.path.isdir(path):
            self.pipeline_dir = path
            wf_crate_filename = os.path.join(path, "ro-crate-metadata.json")
        elif os.path.isfile(path):
            self.pipeline_dir = os.path.dirname(path)
            wf_crate_filename = path

        # Check that the schema file exists
        if self.pipeline_dir is None:
            raise IOError("Could not find pipeline '{}'".format(path))

    def make_workflow_rocrate(self):
        """
        Main process to build an RO Crate object

        NB: At time of writing, rocrate_api.make_workflow_rocrate doesn't seem to support Nextflow
        This code is written by mimicking the code in rocrate_api.make_workflow_rocrate()

        If this works, then the intention would be to move this into rocrate_api.py for a future release
        I've aimed to keep somewhat consistent variable names and code structure because of this
        """

        # Start crate object
        wf_crate = rocrate.rocrate.ROCrate()

        # Set main entity file
        wf_file = wf_crate.add_file(os.path.join(self.pipeline_dir, "nextflow.config"), "nextflow.config")
        wf_crate.set_main_entity(wf_file)

        # Set up language type
        programming_language_entity = rocrate.model.entity.Entity(
            wf_crate,
            "https://www.nextflow.io/",
            properties={
                "@type": ["ComputerLanguage", "SoftwareApplication"],
                "name": "Nextflow",
                "url": "https://www.nextflow.io/",
            },
        )

        wf_file["programmingLanguage"] = programming_language_entity

        # based on ro-crate specification. For workflows: @type is an array
        # with at least File and Workflow as values.
        wf_type = [wf_file["@type"]]
        wf_type.append("Workflow")
        wf_type.append("SoftwareSourceCode")
        wf_file["@type"] = wf_type

        # if the source is a remote URL then add https://schema.org/codeRepository
        # property to it this can be checked by checking if the source is a URL
        # instead of a local path
        if "url" in wf_file.properties().keys():
            wf_file["codeRepository"] = wf_file["url"]

        # Add all other files
        wf_filenames = nf_core.utils.get_wf_files(self.pipeline_dir)
        log.info("Adding {} workflow files".format(len(wf_filenames)))
        for fn in wf_filenames:
            if os.path.basename(fn) == "nextflow.config":
                continue
            wf_crate.add_file(fn, os.path.relpath(fn, self.pipeline_dir))

        return wf_crate

    def add_authors(self):
        """
        Add workflow authors to the crate
        NB: We don't have much metadata here - scope to improve in the future
        """
        self.crate.add_person("#joe", joe_metadata)
