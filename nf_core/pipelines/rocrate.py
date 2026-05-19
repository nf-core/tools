#!/usr/bin/env python
"""Code to deal with pipeline RO (Research Object) Crates"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
import rocrate.rocrate
from git import GitCommandError, InvalidGitRepositoryError
from repo2rocrate.nextflow import NextflowCrateBuilder
from rich.progress import BarColumn, Progress
from rocrate.model.person import Person
from rocrate.rocrate import ROCrate as BaseROCrate

from nf_core.utils import Pipeline

log = logging.getLogger(__name__)


# To identify bots, we look for names that contain "[bot]" or end with "-bot" or "_bot", case-insensitive
BOT_PATTERNS = re.compile(r"\[bot\]|(-bot|_bot)$", re.IGNORECASE)


def _is_bot(name: str) -> bool:
    return bool(BOT_PATTERNS.search(name))


class CustomNextflowCrateBuilder(NextflowCrateBuilder):
    DATA_ENTITIES = NextflowCrateBuilder.DATA_ENTITIES + [
        ("docs/usage.md", "File", "Usage documentation"),
        ("docs/output.md", "File", "Output documentation"),
        ("suborkflows/local", "Dataset", "Pipeline-specific suborkflows"),
        ("suborkflows/nf-core", "Dataset", "nf-core suborkflows"),
        (".nf-core.yml", "File", "nf-core configuration file, configuring template features and linting rules"),
        (".pre-commit-config.yaml", "File", "Configuration file for pre-commit hooks"),
        (".prettierignore", "File", "Ignore file for prettier"),
        (".prettierrc", "File", "Configuration file for prettier"),
    ]


def custom_make_crate(
    root: Path,
    workflow: Path | None = None,
    repo_url: str | None = None,
    wf_name: str | None = None,
    wf_version: str | None = None,
    lang_version: str | None = None,
    ci_workflow: str | None = "nf-test.yml",
    diagram: Path | None = None,
) -> BaseROCrate:
    builder = CustomNextflowCrateBuilder(root, repo_url=repo_url)

    return builder.build(
        workflow,
        wf_name=wf_name,
        wf_version=wf_version,
        lang_version=lang_version,
        license=None,
        ci_workflow=ci_workflow,
        diagram=diagram,
    )


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

        setup_requests_cachedir()

    def create_rocrate(self, json_path: None | Path = None, zip_path: None | Path = None) -> bool:
        """
        Create an RO Crate for a pipeline

        Args:
            outdir (Path): Path to the output directory
            json_path (Path): Path to the metadata file
            zip_path (Path): Path to the zip file

        """

        # Check that the checkout pipeline version is the same as the requested version
        if self.version != "" and self.version != self.pipeline_obj.nf_config.get("manifest.version"):
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
        self.make_workflow_rocrate()

        # Save just the JSON metadata file
        if json_path is not None:
            if json_path.name == "ro-crate-metadata.json":
                json_path = json_path.parent

            log.info(f"Saving metadata file to '{json_path}'")
            self.crate.metadata.write(json_path)

        # Save the whole crate zip file
        if zip_path is not None:
            if zip_path.name != "ro-crate.crate.zip":
                zip_path = zip_path / "ro-crate.crate.zip"
            log.info(f"Saving zip file '{zip_path}")
            self.crate.write_zip(zip_path)

        if json_path is None and zip_path is None:
            log.error("Please provide a path to save the ro-crate file or the zip file.")
            return False

        return True

    def make_workflow_rocrate(self) -> None:
        """
        Create an RO Crate for a pipeline
        """
        if self.pipeline_obj is None:
            raise ValueError("Pipeline object not loaded")

        diagram: Path | None = None
        # find files (metro|tube)_?(map)?.png in the pipeline directory or docs/ using pathlib
        pattern = re.compile(r".*?(metro|tube|subway)_(map).*?\.png", re.IGNORECASE)
        for file in self.pipeline_dir.rglob("*.png"):
            if pattern.match(file.name):
                log.debug(f"Found diagram: {file}")
                diagram = file.relative_to(self.pipeline_dir)
                break

        # Create the RO Crate object

        self.crate = custom_make_crate(
            self.pipeline_dir,
            self.pipeline_dir / "main.nf",
            self.pipeline_obj.nf_config.get("manifest.homePage", ""),
            self.pipeline_obj.nf_config.get("manifest.name", ""),
            self.pipeline_obj.nf_config.get("manifest.version", ""),
            self.pipeline_obj.nf_config.get("manifest.nextflowVersion", ""),
            diagram=diagram,
        )

        # add readme as description
        readme = self.pipeline_dir / "README.md"

        try:
            self.crate.description = readme.read_text()
        except FileNotFoundError:
            log.error(f"Could not find README.md in {self.pipeline_dir}")
        # get license from LICENSE file
        license_file = self.pipeline_dir / "LICENSE"
        try:
            license_text = license_file.read_text()
            if license_text.startswith("MIT"):
                self.crate.license = "MIT"
            else:
                # prompt for license
                log.info("Could not determine license from LICENSE file")
                self.crate.license = input("Please enter the license for this pipeline: ")
        except FileNotFoundError:
            log.error(f"Could not find LICENSE file in {self.pipeline_dir}")

        self.crate.add_jsonld(
            {"@id": "https://nf-co.re/", "@type": "Organization", "name": "nf-core", "url": "https://nf-co.re/"}
        )

        # Set metadata for main entity file
        self.set_main_entity("main.nf")

    def set_main_entity(self, main_entity_filename: str):
        """
        Set the main.nf as the main entity of the crate and add necessary metadata
        """
        if self.crate.mainEntity is None:
            raise ValueError("Main entity not set")

        self.crate.mainEntity.append_to(
            "dct:conformsTo", "https://bioschemas.org/profiles/ComputationalWorkflow/1.0-RELEASE/", compact=True
        )
        # add dateCreated and dateModified, based on the current data
        self.crate.mainEntity.append_to("dateCreated", self.crate.root_dataset.get("dateCreated", ""), compact=True)
        self.crate.mainEntity.append_to(
            "dateModified", str(datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")), compact=True
        )
        self.crate.mainEntity.append_to("sdPublisher", {"@id": "https://nf-co.re/"}, compact=True)
        url = "dev" if self.version.endswith("dev") else self.version
        self.crate.mainEntity.append_to(
            "url", f"https://nf-co.re/{self.crate.name.replace('nf-core/', '')}/{url}/", compact=True
        )
        self.crate.mainEntity.append_to("version", self.version, compact=True)

        # remove duplicate entries for version
        self.crate.mainEntity["version"] = list(set(self.crate.mainEntity["version"]))

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

        self.add_main_authors(self.crate.mainEntity)

        self.crate.mainEntity = self.crate.mainEntity

        self.crate.mainEntity.append_to("license", self.crate.license)
        self.crate.mainEntity.append_to("name", self.crate.name)

        # remove duplicate entries for name
        self.crate.mainEntity["name"] = list(set(self.crate.mainEntity["name"]))

        if "dev" in self.version:
            self.crate.creativeWorkStatus = "InProgress"
        else:
            self.crate.creativeWorkStatus = "Stable"
            if self.pipeline_obj.repo is None:
                log.error(f"Pipeline repository not found in {self.pipeline_dir}")
            else:
                tags = self.pipeline_obj.repo.tags
                if tags:
                    # get the tag for this version
                    for tag in tags:
                        if tag.commit.hexsha == self.pipeline_obj.repo.head.commit.hexsha:
                            self.crate.mainEntity.append_to(
                                "dateCreated",
                                tag.commit.committed_datetime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                compact=True,
                            )

    def add_main_authors(self, wf_file: rocrate.model.entity.Entity) -> None:
        """
        Add workflow authors to the crate
        """
        contributors = []
        if "manifest.contributors" in self.pipeline_obj.nf_config:
            contributors = self.parse_manifest_contributors()
        if not contributors and "manifest.author" in self.pipeline_obj.nf_config:
            if self.pipeline_obj.repo:
                contributors = self.parse_manifest_authors()
            else:
                log.debug("No git repository found. Cannot add contributors.")
                return
        if not contributors:
            log.error("No authors found in pipeline manifest. Proceeding without adding authors to the RO-Crate.")
            return

        for author in contributors:
            log.debug(f"Adding author: {author}")

            properties = {
                k: v
                for k, v in {
                    "name": author["name"],
                    "affiliation": author.get("affiliation"),
                    "url": author.get("github"),
                    "email": author.get("email")
                    or (self.pipeline_obj.repo and self._get_git_email_for_name(author["name"])),
                }.items()
                if v
            }

            author_id = self._get_author_identifier(author)
            author_entity = self.crate.add(Person(self.crate, author_id, properties=properties))
            for mode in author.get("contribution", ["contributor"]):
                wf_file.append_to(mode, author_entity)

    def _get_author_identifier(self, author: dict) -> str | None:
        if orcid := author.get("orcid") or get_orcid(author["name"]):
            return orcid
        if email := author.get("email"):
            return f"#{email}"
        return None

    def _get_git_email_for_name(self, name: str) -> str:
        if self.pipeline_obj.repo is None:
            return ""

        names_to_try: list[str] = []
        if "," in name:
            # Support "First, Last" and "Last, First"
            (one, two) = [n.strip() for n in name.split(",", 1)]
            if one and two:
                names_to_try = [f"{one} {two}", f"{two} {one}"]
            elif one:
                names_to_try = [one]
            elif two:
                names_to_try = [two]
        elif name:
            names_to_try = [name]

        for full_name in names_to_try:
            try:
                email = self.pipeline_obj.repo.git.log(f"--author={full_name}", "--pretty=format:%ae", "-1")
                email = email.strip()
                if email:
                    return email
            except GitCommandError:
                pass
        return ""

    def _make_progress_bar(self):
        return Progress(
            "[bold blue]{task.description}",
            BarColumn(bar_width=None),
            "[magenta]{task.completed} of {task.total}[reset] » [bold yellow]{task.fields[name]}",
            transient=True,
            disable=os.environ.get("HIDE_PROGRESS", None) is not None,
        )

    def parse_manifest_authors(self) -> list:
        # parse manifest.author"
        authors = [a.strip() for a in self.pipeline_obj.nf_config["manifest.author"].split(",")]
        # remove duplicates
        authors = list(set(authors))
        log.debug(f"Authors: {authors}")

        # look at git contributors for author names
        git_contributors: set[str] = set()
        if self.pipeline_obj.repo is not None:
            commits_touching_path = list(self.pipeline_obj.repo.iter_commits(paths="main.nf"))

            for commit in commits_touching_path:
                name = commit.author.name
                # exclude bots
                if name and not _is_bot(name) and name != "Travis CI User":
                    git_contributors.add(name)
        else:
            log.debug("Could not find git contributors")
        log.debug(f"Found {len(git_contributors)} git authors")

        git_authors = []
        with self._make_progress_bar() as progress_bar:
            bump_progress = progress_bar.add_task(
                "Searching for author names on GitHub", total=len(git_contributors), name=""
            )

            for git_author in git_contributors:
                progress_bar.update(bump_progress, advance=1, name=git_author)
                github_name = requests.get(f"https://api.github.com/users/{git_author}").json().get("name")
                if github_name:
                    # remove usernames (just keep names with spaces)
                    if " " in github_name and github_name not in authors:
                        git_authors.append(github_name)
                else:
                    log.debug(f"Could not find name for {git_author}")
        log.debug(f"Git authors: {git_authors}")

        contributors = []
        assert self.pipeline_obj.repo is not None  # mypy
        for name in authors + git_authors:
            log.debug(name)
            struct = {
                "name": name,
                "contribution": ["author" if name in authors else "contributor"],
            }
            contributors.append(struct)

        return contributors

    # Read and parse manifest.contributors. Normalise and fix its fields,
    # and return as a list of dictionaries
    def parse_manifest_contributors(self) -> list:
        field_names = ["name", "affiliation", "github", "contribution", "orcid", "email"]
        # Grab the contributor list and convert to JSON
        # TODO: can be removed once we switch to `nextflow config -o json`
        contributors_str = self.pipeline_obj.nf_config["manifest.contributors"]
        log.debug(f"manifest.contributors: {contributors_str}")
        # JSON uses double quotes, not single quotes
        contributors_str = contributors_str.replace("'", '"')
        for key in field_names:
            # All dictionary keys need to be quoted
            contributors_str = contributors_str.replace(f"{key}:", f'"{key}":')
        # Use curly brackets for dictionaries
        contributors_str = contributors_str.replace("], [", "}, {").replace("[[", "[{").replace("]]", "}]")
        log.debug(f"manifest.contributors (normalised): {contributors_str}")
        try:
            contributors = json.loads(contributors_str)
        except json.JSONDecodeError as exc:
            log.error(
                "Could not parse `manifest.contributors` from nextflow.config. "
                "Expected a list of maps, for example: [[name: 'First Last', github: 'user']]. "
                f"Normalised string passed to JSON parser was: {contributors_str!r}. "
                f"JSON decoding error: {exc}"
            )
            return []

        # Using a progress bar because parsing the git log could be slow
        with self._make_progress_bar() as progress_bar:
            bump_progress = progress_bar.add_task("Searching for author emails", total=len(contributors), name="")

            for author in contributors:
                progress_bar.update(bump_progress, advance=1, name=author.get("name"))

                # Normalise fields
                for key in field_names:
                    if key in author:
                        if isinstance(author[key], str):
                            author[key] = author[key].strip()
                        elif isinstance(author[key], list):
                            author[key] = list(filter(lambda s: s, (s.strip() for s in author[key])))
                        if not author[key]:
                            del author[key]

                # Name is required
                if "name" not in author:
                    log.critical(f"No name field for author: {author}")
                    sys.exit(1)

                # Fix the ORCID URL
                if "orcid" in author:
                    orcid = author["orcid"]
                    if not orcid.startswith("http"):
                        author["orcid"] = "https://orcid.org/" + orcid

                # Fix the GitHub URL
                if "github" in author:
                    if author["github"].startswith("@"):
                        author["github"] = "https://github.com/" + author["github"][1:]
                    elif not author["github"].startswith("http"):
                        author["github"] = "https://github.com/" + author["github"]

        return contributors

    def update_rocrate(self) -> bool:
        """
        Update the rocrate file
        """
        # check if we need to output a json file and/or a zip file based on the file extensions
        # try to find a json file
        json_path: Path | None = None
        potential_json_path = Path(self.pipeline_dir, "ro-crate-metadata.json")
        if potential_json_path.exists():
            json_path = potential_json_path

        # try to find a zip file
        zip_path: Path | None = None
        potential_zip_path = Path(self.pipeline_dir, "ro-crate.crate.zip")
        if potential_zip_path.exists():
            zip_path = potential_zip_path

        return self.create_rocrate(json_path=json_path, zip_path=zip_path)


def get_orcid(name: str) -> str | None:
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
