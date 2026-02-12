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

    def test_view_unknown_type_returns_404(self, client):
        """GET /view?path=file.txt returns 404 (unknown type)."""
        response = client.get("/view", query_string={"path": "file.txt"})
        assert response.status_code == 404
