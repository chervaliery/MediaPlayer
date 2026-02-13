"""Pytest fixtures for route tests."""
import pytest

from app import app as flask_app
import share_store


# Register public route so we can test GET /v/<token> (app normally has only private or only public)
from app import _register_public_routes
_register_public_routes()


@pytest.fixture
def media_root(tmp_path):
    """Create a temporary media root with subdir, image, video, and generic file."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / "video.mkv").write_bytes(b"\x00")
    (tmp_path / "file.txt").write_text("hello")
    (tmp_path / "audio.mp3").write_bytes(b"\xff\xfb\x90\x00")  # minimal mp3-like
    (tmp_path / "unknown.xyz").write_bytes(b"binary")
    return tmp_path.resolve()


@pytest.fixture
def client(media_root):
    """Flask test client with MEDIA_ROOT and DATABASE_PATH patched to temp paths."""
    original_root = flask_app.config["MEDIA_ROOT"]
    original_db = flask_app.config.get("DATABASE_PATH")
    db_path = str(media_root / "shares.db")
    flask_app.config["MEDIA_ROOT"] = media_root
    flask_app.config["DATABASE_PATH"] = db_path
    share_store.init(db_path)
    try:
        with flask_app.test_client() as test_client:
            yield test_client
    finally:
        flask_app.config["MEDIA_ROOT"] = original_root
        flask_app.config["DATABASE_PATH"] = original_db
