"""HTTP-based registry client for nf-core/modules.

Fetches and caches components.json from the nf-core website, providing
the same interface as ModulesRepo without requiring a full git clone.
"""

import json
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import yaml

from nf_core.components.constants import NF_CORE_MODULES_REMOTE
from nf_core.utils import NFCORE_CACHE_DIR, gh_api

log = logging.getLogger(__name__)

COMPONENTS_JSON_URL = "https://nf-co.re/components.json"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/nf-core/modules/{sha}/{path}"
GITHUB_API_BASE = "https://api.github.com/repos/nf-core/modules"


class RegistryClient:
    """
    Drop-in replacement for ModulesRepo for the default nf-core/modules remote.
    Downloads components.json once per session (re-downloading only when ETag changes)
    and installs module files via raw.githubusercontent.com rather than a git clone.
    """

    def __init__(self) -> None:
        self.remote_url = NF_CORE_MODULES_REMOTE
        self.branch = "master"
        self.repo_path = "nf-core"
        self.modules_dir = None
        self.subworkflows_dir = None
        self._components: dict | None = None
        self._by_name: dict[str, dict] = {}
        self._file_cache: dict[str, str] = {}

    @property
    def _cache_path(self) -> Path:
        return Path(NFCORE_CACHE_DIR, "components.json")

    @property
    def _etag_path(self) -> Path:
        return self._cache_path.with_suffix(".etag")

    def _fetch(self) -> bytes | None:
        """Download components.json; returns fresh bytes on 200, None on 304 (cache still valid)."""
        headers: dict[str, str] = {}
        if self._cache_path.exists() and self._etag_path.exists():
            headers["If-None-Match"] = self._etag_path.read_text().strip()

        try:
            resp = requests.get(COMPONENTS_JSON_URL, headers=headers, timeout=30)
            if resp.status_code == 304:
                return None
            resp.raise_for_status()
        except requests.RequestException as e:
            if self._cache_path.exists():
                log.warning(f"Could not reach {COMPONENTS_JSON_URL} ({e}), using cached components.json")
                return None
            raise LookupError(f"Could not fetch components.json and no local cache exists: {e}") from e

        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache_path.write_bytes(resp.content)
        if etag := resp.headers.get("ETag"):
            self._etag_path.write_text(etag)
        return resp.content

    def _load(self) -> dict:
        """Load components.json into memory, fetching first if needed."""
        if self._components is not None:
            return self._components
        fresh = self._fetch()
        content = fresh if fresh is not None else self._cache_path.read_bytes()
        self._components = json.loads(content)
        for component_type in ("modules", "subworkflows"):
            for entry in self._components.get(component_type, []):
                name = self._path_to_name(entry["path"], component_type)
                entry["_name"] = name
                self._by_name[f"{component_type}/{name}"] = entry
        return self._components

    @staticmethod
    def _path_to_name(path: str, component_type: str) -> str:
        """Convert components.json path to nf-core/tools slash-separated name.

        e.g. "modules/nf-core/samtools/index/meta.yml" -> "samtools/index"
        """
        return path.removeprefix(f"{component_type}/nf-core/").removesuffix("/meta.yml")

    def get_avail_components(self, component_type: str, **_kwargs) -> list[str]:
        data = self._load()
        return [self._path_to_name(e["path"], component_type) for e in data.get(component_type, [])]

    def component_exists(self, component_name: str, component_type: str, **_kwargs) -> bool:
        self._load()
        return f"{component_type}/{component_name}" in self._by_name

    def get_latest_component_version(self, component_name: str, component_type: str) -> str | None:
        self._load()
        entry = self._by_name.get(f"{component_type}/{component_name}")
        return entry.get("git_sha") if entry else None

    def _list_component_files(self, component_name: str, component_type: str, commit: str) -> list[str]:
        """List a component's files at a specific commit.

        Uses the file list from components.json when the commit is the registry's latest
        for the component; otherwise queries the GitHub contents API at that ref, since
        the file set may differ between commits.
        """
        entry = self._by_name.get(f"{component_type}/{component_name}")
        if entry and entry.get("git_sha") == commit and entry.get("files"):
            return entry["files"]

        def _list_dir(dir_path: str) -> list[str]:
            resp = gh_api.get(f"{GITHUB_API_BASE}/contents/{dir_path}", params={"ref": commit})
            resp.raise_for_status()
            files: list[str] = []
            for item in resp.json():
                if item["type"] == "file":
                    files.append(item["path"])
                elif item["type"] == "dir":
                    files.extend(_list_dir(item["path"]))
            return files

        return _list_dir(f"{component_type}/nf-core/{component_name}")

    def install_component(self, component_name: str, install_dir: str | Path, commit: str, component_type: str) -> bool:
        """Fetch component files from raw.githubusercontent.com at the given commit SHA."""
        self._load()
        try:
            files = self._list_component_files(component_name, component_type, commit)
        except requests.RequestException as e:
            log.error(f"Could not list files for '{component_name}' at {commit}: {e}")
            return False
        if not files:
            log.error(f"No files found for {component_type[:-1]} '{component_name}' at {commit}")
            return False

        install_path = Path(install_dir, component_name)
        install_path.mkdir(parents=True, exist_ok=True)
        dir_prefix = f"{component_type}/nf-core/{component_name}/"

        def _download(file_path: str) -> None:
            dest = install_path / file_path.removeprefix(dir_prefix)
            dest.parent.mkdir(parents=True, exist_ok=True)
            resp = requests.get(GITHUB_RAW_BASE.format(sha=commit, path=file_path), timeout=30)
            resp.raise_for_status()
            dest.write_bytes(resp.content)

        try:
            with ThreadPoolExecutor(max_workers=4) as pool:
                for future in as_completed([pool.submit(_download, f) for f in files]):
                    future.result()
        except requests.RequestException as e:
            log.error(f"Failed to download files for '{component_name}' at {commit}: {e}")
            # Don't leave a partially-downloaded component behind
            shutil.rmtree(install_path, ignore_errors=True)
            return False

        return True

    def sha_exists_on_branch(self, sha: str) -> bool:
        """Check whether a commit SHA is on the default branch of nf-core/modules via the GitHub API."""
        try:
            resp = gh_api.get(f"{GITHUB_API_BASE}/compare/{self.branch}...{sha}", params={"per_page": 1})
            if resp.status_code != 200:
                return False
            # "identical"/"behind" means the SHA is an ancestor of (i.e. on) the branch
            return resp.json().get("status") in ("identical", "behind")
        except requests.RequestException:
            return False

    def get_commit_info(self, sha: str) -> dict[str, str]:
        resp = gh_api.get(f"{GITHUB_API_BASE}/commits/{sha}")
        resp.raise_for_status()
        data = resp.json()
        return {
            "git_sha": sha,
            "trunc_message": data["commit"]["message"],
            "date": data["commit"]["committer"]["date"],
        }

    def get_file_content(self, path: str, commit: str | None = None) -> str:
        """Fetch a single file from nf-core/modules via raw.githubusercontent.com, memoized per instance."""
        ref = commit or self.branch
        key = f"{ref}:{path}"
        if key not in self._file_cache:
            resp = requests.get(GITHUB_RAW_BASE.format(sha=ref, path=path), timeout=30)
            resp.raise_for_status()
            self._file_cache[key] = resp.text
        return self._file_cache[key]

    def component_files_identical(
        self, component_name: str | Path, base_path: str | Path, commit: str | None, component_type: str
    ) -> dict[str, bool]:
        """
        Check whether local component files are identical to the remote ones at the given commit.

        Mirrors ``SyncedRepo.component_files_identical``: compares ``main.nf`` and ``meta.yml``,
        and a file missing locally or remotely is skipped (left as identical).
        """
        ref = commit or self.branch
        component_files = ["main.nf", "meta.yml"]
        files_identical = dict.fromkeys(component_files, True)
        remote_dir = f"{component_type}/nf-core/{component_name}"
        for file in component_files:
            local_file = Path(base_path, file)
            if not local_file.exists():
                log.debug(f"Could not open file: {local_file}")
                continue
            try:
                resp = requests.get(GITHUB_RAW_BASE.format(sha=ref, path=f"{remote_dir}/{file}"), timeout=30)
                if resp.status_code == 404:
                    log.debug(f"File not found on remote at {ref}: {remote_dir}/{file}")
                    continue
                resp.raise_for_status()
            except requests.RequestException as e:
                # Report "not identical" rather than silently matching on network failure
                log.warning(f"Could not fetch '{remote_dir}/{file}' at {ref} to compare: {e}")
                files_identical[file] = False
                continue
            files_identical[file] = resp.content == local_file.read_bytes()
        return files_identical

    def get_component_git_log(
        self, component_name: str | Path, component_type: str, depth: int | None = None
    ) -> list[dict[str, str]]:
        """Fetch commit history via the GitHub API, paginated until exhausted or ``depth`` commits."""
        dir_path = f"{component_type}/nf-core/{component_name}"
        commits: list[dict[str, str]] = []
        page = 1
        try:
            while depth is None or len(commits) < depth:
                resp = gh_api.get(
                    f"{GITHUB_API_BASE}/commits",
                    params={"path": dir_path, "sha": self.branch, "per_page": 100, "page": page},
                )
                resp.raise_for_status()
                batch = resp.json()
                commits.extend({"git_sha": c["sha"], "trunc_message": c["commit"]["message"]} for c in batch)
                if len(batch) < 100:
                    break
                page += 1
        except requests.RequestException as e:
            log.error(f"Could not fetch git log for '{component_name}': {e}")
        return commits[:depth] if depth is not None else commits

    def verify_sha(self, prompt: bool, sha: str | None) -> bool:
        """Validate --sha / --prompt combination and check SHA exists."""
        if prompt and sha is not None:
            log.error("Cannot use '--sha' and '--prompt' at the same time!")
            return False
        if sha and not self.sha_exists_on_branch(sha):
            log.error(f"Commit SHA '{sha}' doesn't exist in '{self.remote_url}'")
            return False
        return True

    def get_meta_yml(self, component_type: str, component_name: str) -> str | None:
        """Return the meta.yml content for a component as a YAML string."""
        self._load()
        entry = self._by_name.get(f"{component_type}/{component_name}")
        if entry is None or "meta" not in entry:
            return None
        return yaml.dump(entry["meta"], default_flow_style=False)

    @property
    def local_repo_dir(self) -> None:
        """No local clone — callers must guard against None."""
        return None

    def gitless_repo(self) -> str:
        return self.remote_url.removesuffix(".git")
