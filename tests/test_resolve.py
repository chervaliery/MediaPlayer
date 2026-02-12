"""Unit tests for path resolution (path traversal safety)."""
from pathlib import Path

import pytest

from app import resolve_under_root


@pytest.fixture
def media_root(tmp_path):
    """A temporary directory as media root with one subdir and one file."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "file.txt").write_text("ok")
    (tmp_path / "file_at_root.txt").write_text("root")
    return tmp_path.resolve()


def test_empty_path_returns_root(media_root):
    assert resolve_under_root(media_root, "") == media_root
    assert resolve_under_root(media_root, "   ") == media_root


def test_dot_path_returns_root(media_root):
    assert resolve_under_root(media_root, ".") == media_root
    assert resolve_under_root(media_root, "./") == media_root


def test_valid_subdir(media_root):
    got = resolve_under_root(media_root, "sub")
    assert got == media_root / "sub"
    assert got.is_dir()


def test_valid_file(media_root):
    got = resolve_under_root(media_root, "sub/file.txt", must_be_file=True)
    assert got == media_root / "sub" / "file.txt"
    assert got.is_file()


def test_path_traversal_rejected(media_root):
    assert resolve_under_root(media_root, "..") is None
    assert resolve_under_root(media_root, "../etc/passwd") is None
    assert resolve_under_root(media_root, "sub/../../etc/passwd") is None
    assert resolve_under_root(media_root, "sub/../..") is None


def test_must_be_file_rejects_dir(media_root):
    assert resolve_under_root(media_root, "sub", must_be_file=True) is None


def test_must_be_dir_rejects_file(media_root):
    assert resolve_under_root(media_root, "sub/file.txt", must_be_dir=True) is None


def test_nonexistent_under_root(media_root):
    # Path doesn't exist -> resolve() still gives path; we don't require exists
    # unless must_be_file/must_be_dir. So "nonexistent" under root is still
    # considered "under root" and returned. For browse/view we then check
    # is_dir/is_file and get 404. So here we only test that we don't escape.
    got = resolve_under_root(media_root, "nonexistent")
    assert got is not None
    assert got == media_root / "nonexistent"
