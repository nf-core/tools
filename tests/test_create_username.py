import pytest
import nf_core.utils
import nf_core.components.components_utils as cu
import nf_core.modules.modules_repo as mr
from nf_core.components.create import ComponentCreate

class DummyWF:
    def __init__(self, origin_url):
        self.config = {}
        # .dir.git_origin_url is all _get_username() cares about
        self.dir = type("Dir", (), {"git_origin_url": origin_url})

class FakeModulesRepo:
    no_pull_global = False
    def __init__(self, *args, **kwargs):
        pass

@pytest.mark.parametrize("origin_url, username, should_pass", [
    # GitHub uses full regex
    ("git@github.com:nf-core/tools.git",    "@john.doe",    True),
    ("https://github.com/foo/bar.git",      "@foo_bar-1",   True),
    ("https://github.com/foo/bar.git",      "@foo@bar",     False),
    # Non‑GitHub skips full regex
    ("git@gitlab.com:john.doe/proj.git",    "@anything",    True),
    ("ssh://gitea.example/user",            "@user.name",   True),
    ("ssh://gitlab.com/user",               "user.name",    False),
])
def test_username_validation(origin_url, username, should_pass, monkeypatch):
    # Stub nextflow and repo logic
    monkeypatch.setattr(nf_core.utils, "run_cmd", lambda *a, **k: (b"", b""))
    monkeypatch.setattr(mr, "ModulesRepo", FakeModulesRepo)
    monkeypatch.setattr(cu, "get_repo_info", lambda d, p: (d, "pipeline", "org"))

    wf = DummyWF(origin_url)
    cc = object.__new__(ComponentCreate)
    cc.wf = wf
    cc.author = None

    if should_pass:
        # Return valid name once
        monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **k: username)
        cc._get_username()
        assert cc.author == username

    else:
        # Immediately raise to break out of the loop
        def raise_exit(*args, **kwargs):
            raise SystemExit(1)
        monkeypatch.setattr("rich.prompt.Prompt.ask", raise_exit)

        with pytest.raises(SystemExit):
            cc._get_username()