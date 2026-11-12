"""Background updater for the cached nf-core version."""

import json
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from packaging.version import Version


def refresh_version_cache(source_url: str, cache_path: Path) -> None:
    """Fetch and atomically cache the latest nf-core version."""
    with urllib.request.urlopen(source_url, timeout=10) as response:
        remote_version = re.sub(r"[^0-9.]", "", response.read().decode())

    # Do not replace a valid cache with a malformed response.
    Version(remote_version)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache_path.parent) as temporary_dir:
        temporary_path = Path(temporary_dir, cache_path.name)
        temporary_path.write_text(json.dumps({"version": remote_version, "timestamp": time.time()}))
        temporary_path.replace(cache_path)


def main() -> None:
    """Run the background version updater."""
    if len(sys.argv) != 3:
        raise SystemExit("usage: version_updater <source-url> <cache-path>")

    refresh_version_cache(sys.argv[1], Path(sys.argv[2]))


if __name__ == "__main__":
    main()
