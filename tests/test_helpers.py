"""Tests for MIME and file-type helpers."""
from pathlib import Path

import pytest

from app import get_mime, is_audio, is_image, is_text, is_video


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
        (".mp3", "audio/mpeg"),
        (".ogg", "audio/ogg"),
        (".wav", "audio/wav"),
        (".flac", "audio/flac"),
        (".m4a", "audio/mp4"),
        (".txt", "text/plain"),
        (".md", "text/markdown"),
        (".json", "application/json"),
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


def test_is_audio():
    """is_audio True for audio extensions, False otherwise."""
    assert is_audio(Path("x.mp3")) is True
    assert is_audio(Path("x.ogg")) is True
    assert is_audio(Path("x.wav")) is True
    assert is_audio(Path("x.flac")) is True
    assert is_audio(Path("x.m4a")) is True
    assert is_audio(Path("x.mkv")) is False
    assert is_audio(Path("x.txt")) is False
    assert is_audio(Path("x")) is False


def test_is_text():
    """is_text True for text extensions, False otherwise."""
    assert is_text(Path("x.txt")) is True
    assert is_text(Path("x.md")) is True
    assert is_text(Path("x.json")) is True
    assert is_text(Path("x.yaml")) is True
    assert is_text(Path("x.py")) is True
    assert is_text(Path("x.mkv")) is False
    assert is_text(Path("x.mp3")) is False
    assert is_text(Path("x")) is False
