"""HTTP-based registry client for nf-core/modules.

Fetches and caches components.json from the nf-core website, providing
the same interface as ModulesRepo without requiring a full git clone.
"""

import json
import logging
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
        except requests.RequestException as e:
            if self._cache_path.exists():
                log.warning(f"Could not reach {COMPONENTS_JSON_URL} ({e}), using cached components.json")
                return None
            raise LookupError(f"Could not fetch components.json and no local cache exists: {e}") from e

        if resp.status_code == 304:
            return None

        resp.raise_for_status()
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

    def install_component(self, component_name: str, install_dir: str | Path, commit: str, component_type: str) -> bool:
        """Fetch component files from raw.githubusercontent.com at the given commit SHA."""
        self._load()
        entry = self._by_name.get(f"{component_type}/{component_name}")
        if not entry:
            log.error(f"Could not find {component_type[:-1]} '{component_name}' in registry")
            return False

        files: list[str] = entry.get("files", [])
        if not files:
            log.error(f"No file list available for '{component_name}' in registry")
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
                futures = {pool.submit(_download, f): f for f in files}
                for future in as_completed(futures):
                    future.result()
        except requests.RequestException as e:
            log.error(f"Failed to download files for '{component_name}' at {commit}: {e}")
            return False

        return True

    def sha_exists_on_branch(self, sha: str) -> bool:
        """Check whether a commit SHA exists in nf-core/modules via the GitHub API."""
        try:
            resp = gh_api.get(f"{GITHUB_API_BASE}/commits/{sha}")
            return resp.status_code == 200
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

    def component_files_identical(
        self, component_name: str | Path, base_path: str | Path, commit: str, component_type: str
    ) -> dict[str, bool]:
        """Not supported for HTTP registry — no local clone to compare against."""
        return {}

    def get_component_git_log(
        self, component_name: str | Path, component_type: str, depth: int | None = None
    ) -> list[dict[str, str]]:
        """Fetch commit history via the GitHub API (used for interactive --sha selection)."""
        dir_path = f"{component_type}/nf-core/{component_name}"
        try:
            resp = gh_api.get(f"{GITHUB_API_BASE}/commits", params={"path": dir_path, "per_page": depth or 30})
            resp.raise_for_status()
            return [{"git_sha": c["sha"], "trunc_message": c["commit"]["message"]} for c in resp.json()]
        except requests.RequestException as e:
            log.error(f"Could not fetch git log for '{component_name}': {e}")
            return []

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
