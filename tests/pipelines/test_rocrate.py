"""Test the nf-core pipelines rocrate command"""

import json
import re
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import git
import rocrate.rocrate
from git import Repo

import nf_core.pipelines.rocrate
from nf_core.pipelines.bump_version import bump_pipeline_version

from ..test_pipelines import TestPipelines


class MockResponse:
    def __init__(self, payload, status_code=200, url=""):
        self.payload = payload
        self.status_code = status_code
        self.url = url

    def json(self):
        return self.payload


class TestROCrate(TestPipelines):
    """Class for lint tests"""

    def setUp(self) -> None:
        super().setUp()
        # add fake metro map
        Path(self.pipeline_dir, "docs", "images", "nf-core-testpipeline_metro_map.png").touch()
        # commit the changes
        repo = Repo(self.pipeline_dir)
        repo.git.add(A=True)
        repo.index.commit("Initial commit")
        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(self.pipeline_dir)

    def tearDown(self):
        """Clean up temporary files and folders"""

        if self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir)

    def _set_manifest_identity(self, manifest_body: str) -> None:
        config_path = Path(self.pipeline_dir, "nextflow.config")
        config_text = config_path.read_text()
        updated_text, replacements = re.subn(
            r"(?ms)^    contributors\s*=\s*\[\n.*?^    \]\n",
            manifest_body,
            config_text,
            count=1,
        )
        self.assertEqual(replacements, 1)
        config_path.write_text(updated_text)

        self.pipeline_obj = nf_core.utils.Pipeline(self.pipeline_dir)
        self.pipeline_obj._load()
        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(self.pipeline_dir)

    def _commit_main_nf_change(self, author_name: str, email: str, message: str) -> None:
        repo = Repo(self.pipeline_dir)
        main_nf = Path(self.pipeline_dir, "main.nf")
        main_nf.write_text(main_nf.read_text() + f"\n// {message}\n")
        repo.index.add([str(main_nf.relative_to(self.pipeline_dir))])
        actor = git.Actor(author_name, email)
        repo.index.commit(message, author=actor, committer=actor)

    def _mock_requests_get(self, topics=None, github_names=None, orcid_lookup=None):
        topics = topics or ["rna-seq"]
        github_names = github_names or {}
        orcid_lookup = orcid_lookup or {}

        def mocked_requests_get(url, params=None, headers=None, **kwargs):
            if url == "https://nf-co.re/pipelines.json":
                return MockResponse(
                    {"remote_workflows": [{"name": self.pipeline_obj.pipeline_name, "topics": topics}]},
                    url=url,
                )
            if url.startswith("https://api.github.com/users/"):
                username = url.rsplit("/", 1)[-1]
                return MockResponse({"name": github_names.get(username)}, url=url)
            if url == "https://pub.orcid.org/v3.0/search/":
                queried_name = None
                if params is not None and "q" in params:
                    match = re.search(r'family-name:"([^"]+)" AND given-names:"([^"]+)"', params["q"])
                    if match:
                        queried_name = f"{match.group(2)} {match.group(1)}"
                orcid_uri = orcid_lookup.get(queried_name)
                if orcid_uri is None:
                    return MockResponse({"num-found": 0, "result": []}, url=url)
                return MockResponse(
                    {"num-found": 1, "result": [{"orcid-identifier": {"uri": orcid_uri}}]},
                    url=url,
                )
            raise AssertionError(f"Unexpected request during test: {url}")

        return mocked_requests_get

    def _read_crate_graph(self):
        with open(Path(self.pipeline_dir, "ro-crate-metadata.json")) as f:
            return json.load(f)["@graph"]

    def _graph_entity(self, graph, entity_id: str):
        candidate_ids = {entity_id, entity_id.removeprefix("#")}
        for entity in graph:
            if entity.get("@id") in candidate_ids:
                return entity
        self.fail(f"Could not find entity {entity_id}")

    def _graph_person(self, graph, name: str):
        for entity in graph:
            if entity.get("@type") == "Person" and entity.get("name") == name:
                return entity
        self.fail(f"Could not find person {name}")

    def _create_rocrate_with_mocked_requests(self, topics=None, github_names=None, orcid_lookup=None) -> None:
        with mock.patch(
            "nf_core.pipelines.rocrate.requests.get",
            side_effect=self._mock_requests_get(topics=topics, github_names=github_names, orcid_lookup=orcid_lookup),
        ):
            self.assertTrue(self.rocrate_obj.create_rocrate(json_path=self.pipeline_dir))

    def test_rocrate_creation(self):
        """Run the nf-core rocrate command"""

        # Run the command
        assert self.rocrate_obj.create_rocrate(self.pipeline_dir, self.pipeline_dir)

        # Check that the crate was created
        self.assertTrue(Path(self.pipeline_dir, "ro-crate-metadata.json").exists())

        # Check that the entries in the crate are correct
        crate = rocrate.rocrate.ROCrate(self.pipeline_dir)
        entities = crate.get_entities()

        # Check if the correct entities are set:
        for entity in entities:
            entity_json = entity.as_jsonld()
            if entity_json["@id"] == "./":
                self.assertEqual(
                    entity_json.get("name"), f"{self.pipeline_obj.pipeline_prefix}/{self.pipeline_obj.pipeline_name}"
                )
                self.assertEqual(entity_json["mainEntity"], {"@id": "main.nf"})
            elif entity_json["@id"] == "#main.nf":
                self.assertEqual(entity_json["programmingLanguage"], [{"@id": "#nextflow"}])
                self.assertEqual(entity_json["image"], [{"@id": "nf-core-testpipeline_metro_map.png"}])
            # assert there is a metro map
            # elif entity_json["@id"] == "nf-core-testpipeline_metro_map.png": # FIXME waiting for https://github.com/ResearchObject/ro-crate-py/issues/174
            # self.assertEqual(entity_json["@type"], ["File", "ImageObject"])
            # assert that author is set as a person
            elif "name" in entity_json and entity_json["name"] == "Test McTestFace":
                self.assertEqual(entity_json["@type"], "Person")
                # check that it is set as author of the main entity
                if crate.mainEntity is not None:
                    self.assertEqual(crate.mainEntity["author"][0].id, entity_json["@id"])

    def test_rocrate_creation_wrong_pipeline_dir(self):
        """Run the nf-core rocrate command with a wrong pipeline directory"""
        # Run the command

        # Check that it raises a UserWarning
        with self.assertRaises(UserWarning):
            nf_core.pipelines.rocrate.ROCrate(self.pipeline_dir / "bad_dir")

        # assert that the crate was not created
        self.assertFalse(Path(self.pipeline_dir / "bad_dir", "ro-crate-metadata.json").exists())

    def test_rocrate_creation_with_wrong_version(self):
        """Run the nf-core rocrate command with a pipeline version"""
        # Run the command

        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(self.pipeline_dir, version="1.0.0")

        # Check that the crate was created
        with self.assertRaises(SystemExit):
            assert self.rocrate_obj.create_rocrate(self.pipeline_dir, self.pipeline_dir)

    def test_rocrate_creation_without_git(self):
        """Run the nf-core rocrate command with a pipeline version"""

        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(self.pipeline_dir, version="1.0.0")
        # remove git repo
        shutil.rmtree(self.pipeline_dir / ".git")
        # Check that the crate was created
        with self.assertRaises(SystemExit):
            assert self.rocrate_obj.create_rocrate(self.pipeline_dir, self.pipeline_dir)

    def test_rocrate_creation_to_zip(self):
        """Run the nf-core rocrate command with a zip output"""
        assert self.rocrate_obj.create_rocrate(self.pipeline_dir, zip_path=self.pipeline_dir)
        # Check that the crate was created
        self.assertTrue(Path(self.pipeline_dir, "ro-crate.crate.zip").exists())

    def test_rocrate_creation_uses_manifest_author_when_contributors_missing(self):
        """Use manifest.author when manifest.contributors is not defined"""

        self._set_manifest_identity("author = 'Ada Lovelace, Grace Hopper, Ada Lovelace'\n")
        self._create_rocrate_with_mocked_requests()

        graph = self._read_crate_graph()
        workflow = self._graph_entity(graph, "#main.nf")
        person_names = {entity["name"] for entity in graph if entity.get("@type") == "Person"}

        self.assertEqual(person_names, {"Ada Lovelace", "Grace Hopper"})
        self.assertEqual(len(workflow["author"]), 2)

    def test_parse_manifest_authors_adds_git_contributors(self):
        """Enrich manifest.author metadata with contributor names discovered from git history"""

        self._set_manifest_identity("author = 'Ada Lovelace'\n")
        self._commit_main_nf_change("octocat", "octocat@example.com", "Add git contributor")

        with mock.patch(
            "nf_core.pipelines.rocrate.requests.get",
            side_effect=self._mock_requests_get(github_names={"octocat": "Mona Octocat"}),
        ):
            contributors = self.rocrate_obj.parse_manifest_authors()

        contributions_by_name = {contributor["name"]: contributor["contribution"] for contributor in contributors}
        self.assertEqual(contributions_by_name["Ada Lovelace"], ["author"])
        self.assertEqual(contributions_by_name["Mona Octocat"], ["contributor"])

    def test_parse_manifest_contributors_normalises_fields(self):
        """Normalise contributor metadata from Nextflow config and backfill missing email addresses"""

        self._set_manifest_identity(
            """contributors = [
                [
                    name: 'Alice Example',
                    affiliation: '  Example Lab  ',
                    email: '',
                    github: '@alice',
                    contribution: ['author', '', 'maintainer'],
                    orcid: '0000-0001-2345-6789'
                ],
                [
                    name: 'Bob Example',
                    affiliation: '',
                    email: '',
                    github: 'bobdev',
                    contribution: ['contributor', ''],
                    orcid: ''
                ]
            ]
            """
        )

        contributors = self.rocrate_obj.parse_manifest_contributors()
        contributors_by_name = {contributor["name"]: contributor for contributor in contributors}

        self.assertEqual(contributors_by_name["Alice Example"]["affiliation"], "Example Lab")
        self.assertEqual(contributors_by_name["Alice Example"]["github"], "https://github.com/alice")
        self.assertEqual(contributors_by_name["Alice Example"]["orcid"], "https://orcid.org/0000-0001-2345-6789")
        self.assertEqual(contributors_by_name["Alice Example"]["contribution"], ["author", "maintainer"])
        self.assertNotIn("affiliation", contributors_by_name["Bob Example"])
        self.assertEqual(contributors_by_name["Bob Example"]["github"], "https://github.com/bobdev")
        self.assertEqual(contributors_by_name["Bob Example"]["contribution"], ["contributor"])

    def test_get_git_email_for_name(self):
        """Match git author email using the full contributor name, not just the first token"""

        self._commit_main_nf_change("Alex Example", "alex.correct@example.com", "Commit by the right Alex")
        self._commit_main_nf_change("Alex Wrong", "alex.wrong@example.com", "Commit by a different Alex")

        email = self.rocrate_obj._get_git_email_for_name("Alex Example")
        self.assertEqual(email, "alex.correct@example.com")

        email = self.rocrate_obj._get_git_email_for_name("Alex Wrong")
        self.assertEqual(email, "alex.wrong@example.com")

    def test_parse_manifest_contributors_logs_parse_errors(self):
        """Emit a clear error when manifest.contributors cannot be normalised into valid JSON"""

        self._set_manifest_identity(
            """contributors = [
                [
                    name: 'Alice Example',
                    github: alice
                ]
            ]
            """
        )

        with self.assertLogs("nf_core.pipelines.rocrate", level="ERROR") as logs:
            assert self.rocrate_obj.parse_manifest_contributors() == []

        self.assertIn("Could not parse `manifest.contributors`", "\n".join(logs.output))

    def test_rocrate_creation_prefers_manifest_contributors_over_author(self):
        """Prefer manifest.contributors metadata when both contributor fields are present"""

        self._set_manifest_identity(
            """author = 'Ignored Author'
            contributors = [
                [
                    name: 'Preferred Person',
                    affiliation: '',
                    email: 'preferred@example.com',
                    github: '',
                    contribution: ['author'],
                    orcid: ''
                ]
            ]
            """
        )
        self._create_rocrate_with_mocked_requests()

        graph = self._read_crate_graph()
        person_names = {entity["name"] for entity in graph if entity.get("@type") == "Person"}
        preferred_person = self._graph_person(graph, "Preferred Person")

        self.assertEqual(person_names, {"Preferred Person"})
        self.assertEqual(preferred_person["@id"], "#preferred@example.com")

    def test_rocrate_creation_maps_manifest_contributor_roles_and_identifiers(self):
        """Map contributor roles onto RO-Crate properties and keep deterministic identifiers"""

        self._set_manifest_identity(
            """contributors = [
                [
                    name: 'Alice Example',
                    affiliation: 'Example Lab',
                    email: '',
                    github: '@alice',
                    contribution: ['author', 'maintainer'],
                    orcid: '0000-0001-2345-6789'
                ],
                [
                    name: 'Charlie Brown',
                    affiliation: '',
                    email: '',
                    github: '',
                    contribution: ['contributor'],
                    orcid: ''
                ]
            ]
            """
        )
        self._create_rocrate_with_mocked_requests(
            orcid_lookup={"Charlie Brown": "https://orcid.org/0000-0002-2222-2222"}
        )

        graph = self._read_crate_graph()
        workflow = self._graph_entity(graph, "#main.nf")
        alice = self._graph_person(graph, "Alice Example")
        charlie = self._graph_person(graph, "Charlie Brown")

        self.assertEqual(alice["@id"], "https://orcid.org/0000-0001-2345-6789")
        self.assertEqual(charlie["@id"], "https://orcid.org/0000-0002-2222-2222")
        self.assertEqual(workflow["author"], [{"@id": alice["@id"]}])
        self.assertEqual(workflow["maintainer"], [{"@id": alice["@id"]}])
        self.assertEqual(workflow["contributor"], [{"@id": charlie["@id"]}])

    def test_get_author_identifier_allows_missing_identifier(self):
        """Allow contributors without ORCID or email to keep a None identifier"""

        author = {"name": "Charlie Brown"}

        with mock.patch("nf_core.pipelines.rocrate.get_orcid", return_value=None):
            self.assertIsNone(self.rocrate_obj._get_author_identifier(author))

    def test_parse_manifest_contributors_requires_names(self):
        """Abort when a contributor entry is missing a name"""

        self._set_manifest_identity(
            """contributors = [
                [
                    affiliation: 'Example Lab',
                    email: '',
                    github: '',
                    contribution: ['author'],
                    orcid: ''
                ]
            ]
            """
        )

        with self.assertRaises(SystemExit):
            self.rocrate_obj.parse_manifest_contributors()

    def test_rocrate_creation_for_fetchngs(self):
        """Run the nf-core rocrate command with nf-core/fetchngs"""
        tmp_dir = Path(tempfile.mkdtemp())
        # git clone  nf-core/fetchngs
        git.Repo.clone_from("https://github.com/nf-core/fetchngs", tmp_dir / "fetchngs")
        # Run the command
        self.rocrate_obj = nf_core.pipelines.rocrate.ROCrate(tmp_dir / "fetchngs", version="1.12.0")
        assert self.rocrate_obj.create_rocrate(tmp_dir / "fetchngs", self.pipeline_dir)

        # Check that Sateesh Peri is mentioned in creator field

        crate = rocrate.rocrate.ROCrate(self.pipeline_dir)
        entities = crate.get_entities()
        for entity in entities:
            entity_json = entity.as_jsonld()
            if entity_json["@id"] == "#main.nf":
                assert "https://orcid.org/0000-0002-9879-9070" in entity_json["creator"]

        # Clean up
        shutil.rmtree(tmp_dir)

    def test_update_rocrate(self):
        """Run the nf-core rocrate command with a zip output"""

        assert self.rocrate_obj.create_rocrate(json_path=self.pipeline_dir, zip_path=self.pipeline_dir)

        # read the crate json file
        with open(Path(self.pipeline_dir, "ro-crate-metadata.json")) as f:
            crate = json.load(f)

        # check the old version
        self.assertEqual(crate["@graph"][2]["version"][0], "1.0.0dev")
        # check creativeWorkStatus is InProgress
        self.assertEqual(crate["@graph"][0]["creativeWorkStatus"], "InProgress")

        # bump version
        bump_pipeline_version(self.pipeline_obj, "1.1.0")

        # Check that the crate was created
        self.assertTrue(Path(self.pipeline_dir, "ro-crate.crate.zip").exists())

        # Check that the crate was updated
        self.assertTrue(Path(self.pipeline_dir, "ro-crate-metadata.json").exists())

        # read the crate json file
        with open(Path(self.pipeline_dir, "ro-crate-metadata.json")) as f:
            crate = json.load(f)

        # check that the version was updated
        self.assertEqual(crate["@graph"][2]["version"][0], "1.1.0")

        # check creativeWorkStatus is Stable
        self.assertEqual(crate["@graph"][0]["creativeWorkStatus"], "Stable")
