"""Tests for MIME and file-type helpers."""
from pathlib import Path

import pytest

from app import get_mime, is_image, is_video


@pytest.mark.parametrize(
    "path_suffix,expected_mime",
    [
        (".mkv", "video/x-matroska"),
        (".mp4", "video/mp4"),
        (".webm", "video/webm"),
        (".jpg", "image/jpeg"),
        (".jpeg", "image/jpeg"),
        (".png", "image/png"),
        (".gif", "image/gif"),
        (".webp", "image/webp"),
    ],
)
def test_get_mime_known(path_suffix, expected_mime):
    """get_mime returns correct MIME for known extensions."""
    path = Path(f"/fake/dir/file{path_suffix}")
    assert get_mime(path) == expected_mime


def test_get_mime_unknown():
    """get_mime returns None for unknown extension."""
    assert get_mime(Path("/fake/file.unknown")) is None
    assert get_mime(Path("/fake/file")) is None


def test_is_video():
    """is_video True for video extensions, False otherwise."""
    assert is_video(Path("x.mkv")) is True
    assert is_video(Path("x.mp4")) is True
    assert is_video(Path("x.webm")) is True
    assert is_video(Path("x.avi")) is True
    assert is_video(Path("x.mov")) is True
    assert is_video(Path("x.jpg")) is False
    assert is_video(Path("x.png")) is False
    assert is_video(Path("x")) is False


def test_is_image():
    """is_image True for image extensions, False otherwise."""
    assert is_image(Path("x.jpg")) is True
    assert is_image(Path("x.jpeg")) is True
    assert is_image(Path("x.png")) is True
    assert is_image(Path("x.gif")) is True
    assert is_image(Path("x.webp")) is True
    assert is_image(Path("x.mkv")) is False
    assert is_image(Path("x.mp4")) is False
    assert is_image(Path("x")) is False
