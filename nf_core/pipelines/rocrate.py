#!/usr/bin/env python
"""Code to deal with pipeline RO (Research Object) Crates"""

import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Union
from urllib.parse import quote

import requests
import rocrate.model.entity
import rocrate.rocrate
from git import GitCommandError, InvalidGitRepositoryError
from rich.progress import BarColumn, Progress
from rocrate.model.person import Person

from nf_core.pipelines.schema import PipelineSchema
from nf_core.utils import Pipeline

log = logging.getLogger(__name__)


class ROCrate:
    """
    Class to generate an RO Crate for a pipeline

    """

    def __init__(self, pipeline_dir: Path, version="") -> None:
        """
        Initialise the ROCrate object

        Args:
            pipeline_dir (Path): Path to the pipeline directory
            version (str): Version of the pipeline to checkout
        """
        from nf_core.utils import is_pipeline_directory, setup_requests_cachedir

        is_pipeline_directory(pipeline_dir)

        self.pipeline_dir = pipeline_dir
        self.version: str = version
        self.crate: rocrate.rocrate.ROCrate
        self.pipeline_obj = Pipeline(self.pipeline_dir)
        self.pipeline_obj._load()
        self.pipeline_obj.schema_obj = PipelineSchema()
        # Assume we're in a pipeline dir root if schema path not set
        self.pipeline_obj.schema_obj.get_schema_path(self.pipeline_dir)
        self.pipeline_obj.schema_obj.load_schema()

        setup_requests_cachedir()

    def create_ro_crate(
        self, outdir: Path, metadata_path: Union[None, Path] = None, zip_path: Union[None, Path] = None
    ) -> None:
        """
        Create an RO Crate for a pipeline

        Args:
            outdir (Path): Path to the output directory
            metadata_path (Path): Path to the metadata file
            zip_path (Path): Path to the zip file

        """
        import os

        # Set input paths
        try:
            self.set_crate_paths(outdir)
        except OSError as e:
            log.error(e)
            sys.exit(1)

        # Change to the pipeline directory, because the RO Crate doesn't handle relative paths well
        current_path = Path.cwd()
        os.chdir(self.pipeline_dir)

        # Check that the checkout pipeline version is the same as the requested version
        if self.version != "":
            if self.version != self.pipeline_obj.nf_config.get("manifest.version"):
                # using git checkout to get the requested version
                log.info(f"Checking out pipeline version {self.version}")
                if self.pipeline_obj.repo is None:
                    log.error(f"Pipeline repository not found in {self.pipeline_dir}")
                    sys.exit(1)
                try:
                    self.pipeline_obj.repo.git.checkout(self.version)
                    self.pipeline_obj = Pipeline(self.pipeline_dir)
                    self.pipeline_obj._load()
                except InvalidGitRepositoryError:
                    log.error(f"Could not find a git repository in {self.pipeline_dir}")
                    sys.exit(1)
                except GitCommandError:
                    log.error(f"Could not checkout version {self.version}")
                    sys.exit(1)
        self.version = self.pipeline_obj.nf_config.get("manifest.version", "")
        self.make_workflow_ro_crate()

        # Save just the JSON metadata file
        if metadata_path is not None:
            log.info(f"Saving metadata file to '{metadata_path}'")
            # Save the crate to a temporary directory
            tmpdir = Path(tempfile.TemporaryDirectory().name)
            self.crate.write(tmpdir)
            # Now save just the JSON file
            crate_json_fn = Path(tmpdir, "ro-crate-metadata.json")
            if metadata_path.name == "ro-crate-metadata.json":
                crate_json_fn.rename(metadata_path)
            else:
                crate_json_fn.rename(metadata_path / "ro-crate-metadata.json")

        # Save the whole crate zip file
        if zip_path is not None:
            if zip_path.name == "ro-crate.crate.zip":
                log.info(f"Saving zip file '{zip_path}'")
                self.crate.write_zip(zip_path)
            else:
                log.info(f"Saving zip file '{zip_path}/ro-crate.crate.zip;")
                self.crate.write_zip(zip_path / "ro-crate.crate.zip")

        # Change back to the original directory
        os.chdir(current_path)

    def make_workflow_ro_crate(self) -> None:
        """
        Create an RO Crate for a pipeline
        """
        if self.pipeline_obj is None:
            raise ValueError("Pipeline object not loaded")

        # Create the RO Crate object
        self.crate = rocrate.rocrate.ROCrate()

        # Conform to RO-Crate 1.1 and workflowhub-ro-crate
        self.crate.update_jsonld(
            {
                "@id": "ro-crate-metadata.json",
                "conformsTo": [
                    {"@id": "https://w3id.org/ro/crate/1.1"},
                    {"@id": "https://w3id.org/workflowhub/workflow-ro-crate/1.0"},
                ],
            }
        )

        # add readme as description
        readme = Path("README.md")

        try:
            self.crate.description = readme.read_text()
        except FileNotFoundError:
            log.error(f"Could not find README.md in {self.pipeline_dir}")
        # get license from LICENSE file
        license_file = Path("LICENSE")
        try:
            license = license_file.read_text()
            if license.startswith("MIT"):
                self.crate.license = "MIT"
            else:
                # prompt for license
                log.info("Could not determine license from LICENSE file")
                self.crate.license = input("Please enter the license for this pipeline: ")
        except FileNotFoundError:
            log.error(f"Could not find LICENSE file in {self.pipeline_dir}")

        self.crate.name = self.pipeline_obj.nf_config.get("manifest.name")

        self.crate.root_dataset.append_to("version", self.version, compact=True)

        if "dev" in self.version:
            self.crate.CreativeWorkStatus = "InProgress"
        else:
            self.crate.CreativeWorkStatus = "Stable"
            if self.pipeline_obj.repo is None:
                log.error(f"Pipeline repository not found in {self.pipeline_dir}")
            else:
                tags = self.pipeline_obj.repo.tags
                if tags:
                    # get the tag for this version
                    for tag in tags:
                        if tag.commit.hexsha == self.pipeline_obj.repo.head.commit.hexsha:
                            self.crate.root_dataset.append_to(
                                "dateCreated",
                                tag.commit.committed_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                compact=True,
                            )

        self.crate.add_jsonld(
            {"@id": "https://nf-co.re/", "@type": "Organization", "name": "nf-core", "url": "https://nf-co.re/"}
        )

        # Set main entity file
        self.set_main_entity("main.nf")
        # Add all other files
        self.add_workflow_files()

    def set_main_entity(self, main_entity_filename: str):
        """
        Set the main.nf as the main entity of the crate and add necessary metadata
        """
        self.crate.add_workflow(  # sets @type and conformsTo according to Workflow RO-Crate spec
            main_entity_filename,
            dest_path=main_entity_filename,
            main=True,
            lang="nextflow",  # adds the #nextflow entity automatically and connects it to programmingLanguage
            lang_version=self.pipeline_obj.nf_config.get("manifest.nextflowVersion", ""),
        )

        self.crate.mainEntity.append_to(
            "dct:conformsTo", "https://bioschemas.org/profiles/ComputationalWorkflow/1.0-RELEASE/", compact=True
        )
        # add dateCreated and dateModified, based on the current data
        self.crate.mainEntity.append_to("dateCreated", self.crate.root_dataset.get("dateCreated", ""), compact=True)
        self.crate.mainEntity.append_to(
            "dateModified", str(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")), compact=True
        )
        self.crate.mainEntity.append_to("sdPublisher", {"@id": "https://nf-co.re/"}, compact=True)
        if self.version.endswith("dev"):
            url = "dev"
        else:
            url = self.version
        self.crate.mainEntity.append_to(
            "url", f"https://nf-co.re/{self.crate.name.replace('nf-core/','')}/{url}/", compact=True
        )
        self.crate.mainEntity.append_to("version", self.version, compact=True)
        if self.pipeline_obj.schema_obj is not None:
            log.debug("input value")

            schema_input = self.pipeline_obj.schema_obj.schema["definitions"]["input_output_options"]["properties"][
                "input"
            ]
            input_value: Dict[str, Union[str, List[str], bool]] = {
                "@id": "#input",
                "@type": ["PropertyValueSpecification", "FormalParameter"],
                "default": schema_input.get("default", ""),
                "encodingFormat": schema_input.get("mimetype", ""),
                "valueRequired": "input"
                in self.pipeline_obj.schema_obj.schema["definitions"]["input_output_options"]["required"],
                "dct:conformsTo": "https://bioschemas.org/types/FormalParameter/1.0-RELEASE",
            }
            self.crate.add_jsonld(input_value)
            self.crate.mainEntity.append_to(
                "input",
                {"@id": "#input"},
            )

        # get keywords from nf-core website
        remote_workflows = requests.get("https://nf-co.re/pipelines.json").json()["remote_workflows"]
        # go through all remote workflows and find the one that matches the pipeline name
        topics = ["nf-core", "nextflow"]
        for remote_wf in remote_workflows:
            assert self.pipeline_obj.pipeline_name is not None  # mypy
            if remote_wf["name"] == self.pipeline_obj.pipeline_name.replace("nf-core/", ""):
                topics = topics + remote_wf["topics"]
                break

        log.debug(f"Adding topics: {topics}")
        self.crate.mainEntity.append_to("keywords", topics)

        # self.add_main_authors(self.crate.mainEntity)

        self.crate.mainEntity = self.crate.mainEntity

        self.crate.mainEntity.append_to("license", self.crate.license)
        self.crate.mainEntity.append_to("name", self.crate.name)

    def add_main_authors(self, wf_file: rocrate.model.entity.Entity) -> None:
        """
        Add workflow authors to the crate
        """
        # add author entity to crate

        try:
            authors = self.pipeline_obj.nf_config["manifest.author"].split(",")
            # remove spaces
            authors = [a.strip() for a in authors]
            # add manifest authors as maintainer to crate

        except KeyError:
            log.error("No author field found in manifest of nextflow.config")
            return
        # look at git contributors for author names
        try:
            git_contributors: Set[str] = set()
            assert self.pipeline_obj.repo is not None  # mypy
            commits_touching_path = list(self.pipeline_obj.repo.iter_commits(paths="main.nf"))

            for commit in commits_touching_path:
                if commit.author.name is not None:
                    git_contributors.add(commit.author.name)
            # exclude bots
            contributors = {c for c in git_contributors if not c.endswith("bot") and c != "Travis CI User"}

            log.debug(f"Found {len(contributors)} git authors")

            progress_bar = Progress(
                "[bold blue]{task.description}",
                BarColumn(bar_width=None),
                "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[test_name]}",
                transient=True,
                disable=os.environ.get("HIDE_PROGRESS", None) is not None,
            )
            with progress_bar:
                bump_progress = progress_bar.add_task(
                    "Searching for author names on GitHub", total=len(contributors), test_name=""
                )

                for git_author in contributors:
                    progress_bar.update(bump_progress, advance=1, test_name=git_author)
                    git_author = (
                        requests.get(f"https://api.github.com/users/{git_author}").json().get("name", git_author)
                    )
                    if git_author is None:
                        log.debug(f"Could not find name for {git_author}")
                        continue

        except AttributeError:
            log.debug("Could not find git contributors")

        # remove usernames (just keep names with spaces)
        named_contributors = {c for c in contributors if " " in c}

        for author in named_contributors:
            log.debug(f"Adding author: {author}")
            orcid = get_orcid(author)
            author_entitity = self.crate.add(
                Person(self.crate, orcid if orcid is not None else "#" + quote(author), properties={"name": author})
            )
            wf_file.append_to("creator", author_entitity)
            if author in authors:
                wf_file.append_to("maintainer", author_entitity)

    def add_workflow_files(self):
        """
        Add workflow files to the RO Crate
        """
        import re

        import nf_core.utils

        wf_filenames = nf_core.utils.get_wf_files(Path.cwd())
        # exclude github action files
        wf_filenames = [fn for fn in wf_filenames if not fn.startswith(".github/") and not fn == "main.nf"]
        log.debug(f"Adding {len(wf_filenames)} workflow files")
        # find all main.nf files inside modules/nf-core and subworkflows/nf-core
        component_files = [
            fn
            for fn in wf_filenames
            if ((fn.startswith("modules/nf-core") or fn.startswith("subworkflows/nf-core")) and fn.endswith("main.nf"))
        ]

        wf_dirs = [str(Path(fn).parent) for fn in component_files]
        for wf_dir in wf_dirs:
            if Path(wf_dir).exists():
                log.debug(f"Adding workflow directory: {wf_dir}")
                component_type = wf_dir.split("/")[0]
                component_name = wf_dir.replace(component_type + "/nf-core/", "").replace("/", "_")
                self.crate.add_directory(
                    wf_dir,
                    dest_path=wf_dir,
                    properties={
                        "description": f"nf-core {component_type} [{component_name}](https://nf-co.re/{component_type}/{component_name}) installed from the [nf-core/modules repository](https://github.com/nf-core/modules/)."
                    },
                )
        wf_locals = [
            str(Path(fn).parent)
            for fn in wf_filenames
            if fn.startswith("modules/local") or fn.startswith("subworkflows/local") and fn.endswith("main.nf")
        ]

        for wf_dir in wf_locals:
            log.debug(f"Adding workflow directory: {wf_dir}")
            component_type = wf_dir.split("/")[0].rstrip("s")
            component_name = wf_dir.replace(component_type + "/local/", "").replace("/", "_")

            self.crate.add_directory(wf_dir, dest_path=wf_dir, properties={"description": f"local {component_type}"})
        # go through all files that are not part of directories inside wf_dirs
        wf_filenames = [
            fn for fn in wf_filenames if not any(fn.startswith(str(wf_dir)) for wf_dir in wf_dirs + wf_locals)
        ]
        for fn in wf_filenames:
            # add nextflow language to .nf and .config files
            if fn.endswith(".nf") or fn.endswith(".config") or fn.endswith(".nf.test"):
                log.debug(f"Adding workflow file: {fn}")
                self.crate.add_file(fn, dest_path=fn, properties={"programmingLanguage": {"@id": "#nextflow"}})
                continue
            if fn.endswith(".png"):
                log.debug(f"Adding workflow image file: {fn}")
                self.crate.add_jsonld({"@id": fn, "@type": ["File", "ImageObject"]})
                if re.search(r"(metro|tube)_?(map)?", fn) and self.crate.mainEntity is not None:
                    # check if image is set in main entity
                    if self.crate.mainEntity.get("image"):
                        log.info(
                            f"Main entity already has an image: {self.crate.mainEntity.get('image')}, replacing it with: {fn}"
                        )
                    else:
                        log.info(f"Setting main entity image to: {fn}")
                    self.crate.update_jsonld({"@id": "#" + fn, "about": {"@id": self.crate.mainEntity.id}})
                    self.crate.mainEntity.append_to("image", {"@id": Path(fn).name})
                continue
            if fn.endswith(".md"):
                log.debug(f"Adding file: {fn}")
                self.crate.add_file(fn, dest_path=fn, properties={"encodingFormat": "text/markdown"})
                continue
            else:
                log.debug(f"Adding file: {fn}")
                self.crate.add_file(fn, dest_path=fn)
                continue

    def set_crate_paths(self, path: Path) -> None:
        """Given a pipeline name, directory, or path, set wf_crate_filename"""

        if path.is_dir():
            self.pipeline_dir = path
            # wf_crate_filename = path / "ro-crate-metadata.json"
        elif path.is_file():
            self.pipeline_dir = path.parent
            # wf_crate_filename = path

        # Check that the schema file exists
        if self.pipeline_dir is None:
            raise OSError(f"Could not find pipeline '{path}'")


def get_orcid(name: str) -> Optional[str]:
    """
    Get the ORCID for a given name

    Args:
        name (str): Name of the author

    Returns:
        str: ORCID URI or None
    """
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
        log.info(f"API request to ORCID unsuccessful. Status code: {response.status_code}")
        return None
