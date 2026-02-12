"""Pytest fixtures for route tests."""
import pytest

from app import app as flask_app


@pytest.fixture
def media_root(tmp_path):
    """Create a temporary media root with subdir, image, video, and generic file."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "video.mkv").write_bytes(b"\x00")
    (tmp_path / "file.txt").write_text("hello")
    (tmp_path / "unknown.xyz").write_bytes(b"binary")
    return tmp_path.resolve()


@pytest.fixture
def client(media_root):
    """Flask test client with MEDIA_ROOT patched to a temporary directory."""
    original = flask_app.config["MEDIA_ROOT"]
    flask_app.config["MEDIA_ROOT"] = media_root
    try:
        with flask_app.test_client() as test_client:
            yield test_client
    finally:
        flask_app.config["MEDIA_ROOT"] = original
