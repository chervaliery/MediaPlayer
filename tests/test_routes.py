"""Tests for Flask routes (browse and view)."""


class TestBrowse:
    """Tests for the browse route."""

    def test_browse_root_returns_200_and_list(self, client):
        """GET / returns 200 and lists root contents."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Browse" in response.data
        assert b"subdir" in response.data
        assert b"image.png" in response.data
        assert b"video.mkv" in response.data
        assert b"file.txt" in response.data
        assert b"audio.mp3" in response.data
        assert b"unknown.xyz" in response.data

    def test_browse_path_traversal_returns_403(self, client):
        """GET /?path=.. returns 403."""
        response = client.get("/", query_string={"path": ".."})
        assert response.status_code == 403

    def test_browse_subdir_returns_200(self, client):
        """GET /?path=subdir returns 200 and lists subdir (empty)."""
        response = client.get("/", query_string={"path": "subdir"})
        assert response.status_code == 200
        assert b"subdir" in response.data or b"/" in response.data

    def test_browse_file_redirects_to_view(self, client):
        """GET /?path=image.png returns 302 to /view?path=image.png."""
        response = client.get("/", query_string={"path": "image.png"})
        assert response.status_code == 302
        assert "/view" in response.location
        assert "path=image.png" in response.location


class TestView:
    """Tests for the view route."""

    def test_view_path_traversal_returns_403(self, client):
        """GET /view?path=../etc/passwd returns 403."""
        response = client.get("/view", query_string={"path": "../etc/passwd"})
        assert response.status_code == 403

    def test_view_missing_file_returns_404(self, client):
        """GET /view?path=nonexistent returns 403 or 404."""
        response = client.get("/view", query_string={"path": "nonexistent"})
        assert response.status_code in (403, 404)

    def test_view_image_with_html_accept_returns_viewer(self, client):
        """GET /view?path=image.png with Accept: text/html returns 200 and viewer HTML."""
        response = client.get(
            "/view",
            query_string={"path": "image.png"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"<img" in response.data or b"image" in response.data.lower()

    def test_view_image_without_html_returns_image(self, client):
        """GET /view?path=image.png without HTML returns 200 and image content type."""
        response = client.get("/view", query_string={"path": "image.png"})
        assert response.status_code == 200
        assert response.content_type.startswith("image/")

    def test_view_video_with_html_accept_returns_viewer(self, client):
        """GET /view?path=video.mkv with Accept: text/html returns 200 and video viewer."""
        response = client.get(
            "/view",
            query_string={"path": "video.mkv"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"<video" in response.data or b"video" in response.data.lower()

    def test_view_video_without_html_returns_video_mime(self, client):
        """GET /view?path=video.mkv without HTML returns 200 and video MIME."""
        response = client.get("/view", query_string={"path": "video.mkv"})
        assert response.status_code == 200
        assert "video" in (response.content_type or "")

    def test_view_unknown_type_returns_viewer(self, client):
        """GET /view?path=unknown.xyz returns 200 and unknown-type viewer with download."""
        response = client.get(
            "/view",
            query_string={"path": "unknown.xyz"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"Unknown file type" in response.data
        assert b"Download" in response.data

    def test_view_audio_with_html_accept_returns_viewer(self, client):
        """GET /view?path=audio.mp3 with Accept: text/html returns 200 and audio viewer."""
        response = client.get(
            "/view",
            query_string={"path": "audio.mp3"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"<audio" in response.data
        assert b"audio.mp3" in response.data
        assert b"Download" in response.data

    def test_view_audio_without_html_returns_audio_mime(self, client):
        """GET /view?path=audio.mp3 without HTML returns 200 and audio content type."""
        response = client.get("/view", query_string={"path": "audio.mp3"})
        assert response.status_code == 200
        assert "audio" in (response.content_type or "")

    def test_view_text_with_html_accept_returns_viewer(self, client):
        """GET /view?path=file.txt with Accept: text/html returns 200 and text in pre."""
        response = client.get(
            "/view",
            query_string={"path": "file.txt"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"hello" in response.data
        assert b"file.txt" in response.data
        assert b"Download" in response.data

    def test_view_text_without_html_returns_text(self, client):
        """GET /view?path=file.txt without HTML returns 200 and text body."""
        response = client.get("/view", query_string={"path": "file.txt"})
        assert response.status_code == 200
        assert response.data == b"hello"

    def test_view_text_too_large_returns_message(self, client, media_root):
        """GET /view?path=large.txt with file over limit returns message and download."""
        from app import TEXT_VIEW_MAX_BYTES

        large = media_root / "large.txt"
        large.write_bytes(b"x" * (TEXT_VIEW_MAX_BYTES + 1))
        response = client.get(
            "/view",
            query_string={"path": "large.txt"},
            headers={"Accept": "text/html"},
        )
        assert response.status_code == 200
        assert b"File too large to display" in response.data
        assert b"Download" in response.data

    def test_view_download_returns_attachment(self, client):
        """GET /view?path=file.txt&download=1 returns attachment with content."""
        response = client.get(
            "/view",
            query_string={"path": "file.txt", "download": "1"},
        )
        assert response.status_code == 200
        assert response.data == b"hello"
        disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in disposition
