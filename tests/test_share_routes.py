"""Tests for share routes and public token view (GET /v/<token>)."""


class TestShare:
    """Tests for share routes (private mode)."""

    def test_get_share_form_returns_200(self, client):
        """GET /share?path=file.txt returns 200 and form."""
        response = client.get("/share", query_string={"path": "file.txt"})
        assert response.status_code == 200
        assert b"Share link" in response.data
        assert b"file.txt" in response.data
        assert b"Get link" in response.data

    def test_post_share_creates_and_redirects_to_result(self, client):
        """POST /share with path creates share and redirects to share/result."""
        response = client.post(
            "/share",
            data={"path": "file.txt", "expires": "default"},
        )
        assert response.status_code == 302
        assert "/share/result" in response.location
        assert "token=" in response.location

    def test_share_result_shows_public_url(self, client):
        """Create share then GET /share/result?token=... shows public URL."""
        r = client.post("/share", data={"path": "file.txt", "expires": "never"})
        assert r.status_code == 302
        token = r.location.split("token=")[1].split("&")[0]
        resp = client.get("/share/result", query_string={"token": token})
        assert resp.status_code == 200
        assert b"/v/" in resp.data
        assert token.encode() in resp.data

    def test_post_share_reuse_returns_existing_token(self, client):
        """POST /share twice for same path redirects to result with same token."""
        r1 = client.post("/share", data={"path": "image.png", "expires": "never"})
        r2 = client.post("/share", data={"path": "image.png", "expires": "never"})
        assert r1.status_code == 302 and r2.status_code == 302
        token1 = r1.location.split("token=")[1].split("&")[0]
        token2 = r2.location.split("token=")[1].split("&")[0]
        assert token1 == token2

    def test_share_revoke_redirects(self, client):
        """POST /share/revoke revokes and redirects to result."""
        r = client.post("/share", data={"path": "file.txt", "expires": "never"})
        token = r.location.split("token=")[1].split("&")[0]
        resp = client.post("/share/revoke", data={"token": token})
        assert resp.status_code == 302
        assert "revoked" in resp.location or "/share/result" in resp.location


class TestViewByToken:
    """Tests for GET /v/<token> (public route)."""

    def test_v_valid_token_returns_200(self, client):
        """GET /v/<token> with valid token returns 200 and content."""
        r = client.post("/share", data={"path": "file.txt", "expires": "never"})
        token = r.location.split("token=")[1].split("&")[0]
        resp = client.get(f"/v/{token}", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert b"hello" in resp.data or b"file.txt" in resp.data

    def test_v_valid_token_stream_url_in_viewer(self, client):
        """GET /v/<token> with Accept: text/html returns viewer with stream_url."""
        client.post("/share", data={"path": "image.png", "expires": "never"})
        r = client.post("/share", data={"path": "image.png", "expires": "never"})
        token = r.location.split("token=")[1].split("&")[0]
        resp = client.get(f"/v/{token}", headers={"Accept": "text/html"})
        assert resp.status_code == 200
        assert b"<img" in resp.data
        assert f"/v/{token}".encode() in resp.data

    def test_v_invalid_token_returns_404(self, client):
        """GET /v/invalidtoken returns 404."""
        resp = client.get("/v/nonexistenttoken123")
        assert resp.status_code == 404

    def test_v_revoked_token_returns_404(self, client):
        """GET /v/<token> after revoke returns 404."""
        client.post("/share", data={"path": "file.txt", "expires": "never"})
        r = client.post("/share", data={"path": "file.txt", "expires": "never"})
        token = r.location.split("token=")[1].split("&")[0]
        client.post("/share/revoke", data={"token": token})
        resp = client.get(f"/v/{token}")
        assert resp.status_code == 404
