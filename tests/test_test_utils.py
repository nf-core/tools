import tempfile
from pathlib import Path

import pytest

from .utils import set_wd, with_temporary_file, with_temporary_folder


def test_with_temporary_file():
    @with_temporary_file
    def tmp_file_exists(tmp_file):
        assert Path(tmp_file.name).exists()

    tmp_file_exists()


def test_does_not_exist_after():
    tmp_file = with_temporary_file(lambda x: x.name)()
    assert not Path(tmp_file).exists()


def test_with_temporary_folder():
    @with_temporary_folder
    def tmp_folder_exists(tmp_folder):
        assert Path(tmp_folder).exists()

    tmp_folder_exists()


def test_tmp_folder_does_not_exist_after():
    tmp_folder = with_temporary_folder(lambda x: x)()
    assert not Path(tmp_folder).exists()


def test_set_wd():
    with tempfile.TemporaryDirectory() as tmpdirname:
        with set_wd(tmpdirname):
            context_wd = Path().resolve()
        assert context_wd == Path(tmpdirname).resolve()
        assert context_wd != Path().resolve()


def test_set_wd_revert_on_raise():
    wd_before_context = Path().resolve()
    with tempfile.TemporaryDirectory() as tmpdirname:
        with pytest.raises(Exception):
            with set_wd(tmpdirname):
                raise Exception
    assert wd_before_context == Path().resolve()
