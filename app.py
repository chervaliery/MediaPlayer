"""
Minimalist media browser: browse dirs under a configured root, stream video, display images.
Supports mode=private (browse, view, share) or mode=public (token-only view).
"""
import os
import re
from pathlib import Path

import yaml
from flask import Flask, abort, redirect, render_template, request, send_file, url_for

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

_CONFIG_PATH_ENV = os.environ.get("PLAYER_CONFIG")
if _CONFIG_PATH_ENV is not None:
    CONFIG_PATH = _CONFIG_PATH_ENV
else:
    _app_dir = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(_app_dir, "config.yaml")


def load_config(path: str) -> dict:
    """Load and return config dict from a YAML file. Must contain 'media_root'."""
    with open(path, "r", encoding="utf-8") as config_file:
        data = yaml.safe_load(config_file)
    if not data or "media_root" not in data:
        raise ValueError("config must contain 'media_root'")
    return data


def _apply_config(config: dict) -> tuple[Path, str]:
    """Validate config and return (MEDIA_ROOT, MODE)."""
    mode = config.get("mode", "private")
    if mode not in ("private", "public"):
        raise ValueError("config mode must be 'private' or 'public'")
    root = Path(config["media_root"]).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"media_root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"media_root is not a directory: {root}")
    if mode == "public" and not config.get("database"):
        raise ValueError("config database is required when mode is public")
    if mode == "private" and config.get("database") and "share_default_expiry_seconds" not in config:
        raise ValueError("config share_default_expiry_seconds required when database is set (private)")
    return root, mode


_CONFIG = load_config(CONFIG_PATH)
_MEDIA_ROOT, _MODE = _apply_config(_CONFIG)

app = Flask(__name__)
app.config["MEDIA_ROOT"] = _MEDIA_ROOT
app.config["MODE"] = _MODE
app.config["DATABASE_PATH"] = _CONFIG.get("database")
app.config["SHARE_DEFAULT_EXPIRY_SECONDS"] = _CONFIG.get("share_default_expiry_seconds", 86400)
app.config["PUBLIC_BASE_URL"] = _CONFIG.get("public_base_url", "").rstrip("/")

if _MODE == "private" and app.config["DATABASE_PATH"]:
    import share_store
    share_store.init(app.config["DATABASE_PATH"])


@app.context_processor
def _inject_template_context():
    """Expose has_browse so base.html can avoid url_for('browse') in public mode."""
    return {"has_browse": app.config.get("MODE") == "private"}


# -----------------------------------------------------------------------------
# Unicode sanitization (surrogates break URL encoding and UTF-8 responses)
# -----------------------------------------------------------------------------

_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")


def _sanitize_unicode(value: str) -> str:
    """Replace surrogate code points so the string is safe for UTF-8 (URLs, responses)."""
    return _SURROGATE_RE.sub("\ufffd", value)


# -----------------------------------------------------------------------------
# Safe path resolution (no path traversal)
# -----------------------------------------------------------------------------


def resolve_under_root(
    root: Path,
    relative: str,
    *,
    must_be_file: bool = False,
    must_be_dir: bool = False,
) -> Path | None:
    """
    Resolve a relative path under root. Returns absolute Path or None if invalid.
    Prevents path traversal (e.g. .. or symlinks outside root).
    """
    parts = [part for part in relative.strip().split(os.sep) if part and part != "."]
    if ".." in parts:
        return None
    candidate = (root / os.path.join(*parts)) if parts else root
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    root_real = root.resolve()
    try:
        under_root = resolved == root_real or resolved.is_relative_to(root_real)
    except AttributeError:
        try:
            resolved.relative_to(root_real)
            under_root = True
        except ValueError:
            under_root = False
    if not under_root or (must_be_file and not resolved.is_file()) or (must_be_dir and not resolved.is_dir()):
        return None
    return resolved


def resolve_safe(relative: str, must_be_file: bool = False, must_be_dir: bool = False):
    """Resolve under app's MEDIA_ROOT. Returns Path or None."""
    return resolve_under_root(
        app.config["MEDIA_ROOT"],
        relative,
        must_be_file=must_be_file,
        must_be_dir=must_be_dir,
    )


# -----------------------------------------------------------------------------
# MIME types
# -----------------------------------------------------------------------------

VIDEO_EXTENSIONS = {".mkv", ".mp4", ".webm", ".avi", ".mov"}
VIDEO_MIME = {
    ".mkv": "video/x-matroska",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

AUDIO_EXTENSIONS = {".mp3", ".ogg", ".wav", ".flac", ".m4a", ".aac"}
AUDIO_MIME = {
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}

TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".xml", ".csv", ".log",
    ".py", ".html", ".htm", ".css", ".js", ".yaml", ".yml", ".ini", ".cfg",
}
TEXT_MIME = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".json": "application/json",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".log": "text/plain",
    ".py": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".js": "application/javascript",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".ini": "text/plain",
    ".cfg": "text/plain",
}

# Max bytes to load for text view (512 KB)
TEXT_VIEW_MAX_BYTES = 512 * 1024


def get_mime(path: Path) -> str | None:
    """Return MIME type for path by extension, or None if unknown."""
    ext = path.suffix.lower()
    if ext in VIDEO_MIME:
        return VIDEO_MIME[ext]
    if ext in IMAGE_MIME:
        return IMAGE_MIME[ext]
    if ext in AUDIO_MIME:
        return AUDIO_MIME[ext]
    if ext in TEXT_MIME:
        return TEXT_MIME[ext]
    return None


def is_video(path: Path) -> bool:
    """Return True if path has a known video extension."""
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_image(path: Path) -> bool:
    """Return True if path has a known image extension."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


def is_audio(path: Path) -> bool:
    """Return True if path has a known audio extension."""
    return path.suffix.lower() in AUDIO_EXTENSIONS


def is_text(path: Path) -> bool:
    """Return True if path has a known text extension."""
    return path.suffix.lower() in TEXT_EXTENSIONS


def _file_view_type(path: Path) -> str:
    """Return view type: video, image, audio, text, or unknown."""
    if is_video(path):
        return "video"
    if is_image(path):
        return "image"
    if is_audio(path):
        return "audio"
    if is_text(path):
        return "text"
    return "unknown"


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


def redirect_to_view(rel_path: str):
    """Redirect to the view route for the given relative path."""
    return redirect(url_for("view", path=rel_path))


_VIEW_TEMPLATES = {
    "video": "view_video.html",
    "image": "view_image.html",
    "audio": "view_audio.html",
    "unknown": "view_unknown.html",
}


def _render_file_view(view_type: str, resolved: Path, view_kwargs: dict):
    """Return the HTML viewer response for the given type."""
    if view_type == "text":
        try:
            size = resolved.stat().st_size
            if size > TEXT_VIEW_MAX_BYTES:
                return render_template(
                    "view_text.html",
                    **view_kwargs,
                    content=None,
                    message="File too large to display.",
                )
            content = resolved.read_bytes().decode("utf-8", errors="replace")
            return render_template(
                "view_text.html", **view_kwargs, content=content, message=None
            )
        except OSError:
            abort(404)
    template = _VIEW_TEMPLATES.get(view_type, "view_unknown.html")
    return render_template(template, **view_kwargs)


def serve_resolved_file(
    resolved: Path,
    stream_url: str,
    download_url: str,
    filename: str,
    show_share: bool,
    path_for_share: str,
):
    """
    Handle request for a resolved file: download, HTML viewer, or stream.
    path_for_share is the path query for Share link (private only); unused when show_share is False.
    """
    view_type = _file_view_type(resolved)
    view_kwargs = {
        "stream_url": stream_url,
        "download_url": download_url,
        "filename": filename,
        "show_share": show_share,
        "path": path_for_share,
    }
    if request.args.get("download", "").lower() in ("1", "true", "yes"):
        mime = get_mime(resolved) or "application/octet-stream"
        return send_file(
            resolved,
            mimetype=mime,
            as_attachment=True,
            download_name=resolved.name,
        )
    if request.args.get("embed", "").lower() in ("1", "true", "yes") or (
        "text/html" in request.headers.get("Accept", "")
    ):
        return _render_file_view(view_type, resolved, view_kwargs)
    return _stream_file(view_type, resolved)


def _stream_file(view_type: str, resolved: Path):
    """Return the streaming response for the given type."""
    stream_mime = get_mime(resolved)
    if view_type == "video":
        return send_file(
            resolved,
            mimetype=stream_mime or "video/unknown",
            conditional=True,
            as_attachment=False,
        )
    mime_map = {
        "image": stream_mime or "image/unknown",
        "audio": stream_mime or "audio/unknown",
        "text": stream_mime or "text/plain",
    }
    if view_type in mime_map:
        return send_file(
            resolved, mimetype=mime_map[view_type], as_attachment=False
        )
    return send_file(
        resolved,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=resolved.name,
    )


def _register_private_routes():
    """Register routes for mode=private: browse, view, share."""

    @app.route("/")
    def browse():
        """List directory contents under media root, or redirect to view for files."""
        raw = request.args.get("path", "").strip()
        resolved = resolve_safe(raw, must_be_dir=False)
        if resolved is None:
            abort(403)
        if resolved.is_file():
            return redirect_to_view(raw)
        if not resolved.is_dir():
            abort(404)
        root = app.config["MEDIA_ROOT"]
        try:
            entries = sorted(
                list(resolved.iterdir()),
                key=lambda entry: (not entry.is_dir(), entry.name.lower()),
            )
        except OSError:
            abort(404)
        try:
            rel_dir = resolved.relative_to(root)
            rel_parts = list(rel_dir.parts)
        except ValueError:
            rel_parts = []
        items = []
        for entry in entries:
            name = entry.name
            if entry.is_dir():
                sub_rel = os.path.join(*rel_parts, name) if rel_parts else name
                items.append({
                    "name": _sanitize_unicode(name) + "/",
                    "path": _sanitize_unicode(sub_rel),
                    "is_dir": True,
                    "icon": "dir",
                })
            else:
                sub_rel = os.path.join(*rel_parts, name) if rel_parts else name
                if is_video(entry):
                    icon = "video"
                elif is_image(entry):
                    icon = "image"
                elif is_audio(entry):
                    icon = "audio"
                elif is_text(entry):
                    icon = "text"
                else:
                    icon = "file"
                items.append({
                    "name": _sanitize_unicode(name),
                    "path": _sanitize_unicode(sub_rel),
                    "is_dir": False,
                    "icon": icon,
                })
        current_path = _sanitize_unicode("/" + "/".join(rel_parts)) if rel_parts else "/"
        parent_parts = rel_parts[:-1] if rel_parts else []
        parent_path = _sanitize_unicode(os.path.join(*parent_parts)) if parent_parts else ""
        return render_template(
            "browse.html",
            current_path=current_path,
            parent_path=parent_path,
            items=items,
        )

    @app.route("/view")
    def view():
        """Stream file or return viewer HTML; supports ?download=1 for attachment."""
        raw = request.args.get("path", "").strip()
        resolved = resolve_safe(raw, must_be_file=True)
        if resolved is None:
            abort(403)
        if not resolved.is_file():
            abort(404)
        path_safe = _sanitize_unicode(raw)
        filename = _sanitize_unicode(resolved.name)
        stream_url = url_for("view", path=path_safe)
        download_url = url_for("view", path=path_safe, download=1)
        return serve_resolved_file(
            resolved, stream_url, download_url, filename,
            show_share=True, path_for_share=path_safe,
        )

    @app.route("/share", methods=["GET", "POST"])
    def share():
        """GET: show share form. POST: create or reuse share, redirect to result."""
        raw = request.args.get("path", "").strip() if request.method == "GET" else request.form.get("path", "").strip()
        if not raw:
            abort(400)
        resolved = resolve_safe(raw, must_be_file=True)
        if resolved is None or not resolved.is_file():
            abort(403)
        path_safe = _sanitize_unicode(raw)
        db_path = app.config.get("DATABASE_PATH")
        if not db_path:
            abort(503)
        import share_store
        if request.method == "GET":
            existing = share_store.get_active_by_file_path(db_path, raw)
            if existing:
                return redirect(url_for("share_result", token=existing["token"]))
            return render_template("share_form.html", path=path_safe)
        # POST
        expires = request.form.get("expires", "default")
        custom_value = request.form.get("custom_value", "").strip()
        custom_unit = request.form.get("custom_unit", "hours")
        existing = share_store.get_active_by_file_path(db_path, raw)
        if existing:
            return redirect(url_for("share_result", token=existing["token"]))
        if expires == "never":
            expires_seconds = None
        elif expires == "custom" and custom_value.isdigit():
            val = int(custom_value)
            if custom_unit == "days":
                val *= 86400
            else:
                val *= 3600
            expires_seconds = val
        else:
            expires_seconds = app.config["SHARE_DEFAULT_EXPIRY_SECONDS"]
        token = share_store.create_share(db_path, raw, expires_seconds)
        return redirect(url_for("share_result", token=token))

    @app.route("/share/result")
    def share_result():
        """Show share result with public URL, copy and revoke."""
        token = request.args.get("token", "").strip()
        if not token:
            abort(400)
        base = (app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
        if not base:
            base = request.url_root.rstrip("/")
        public_url = f"{base}/v/{token}"
        revoked = request.args.get("revoked", "").strip() == "1"
        return render_template("share_result.html", token=token, public_url=public_url, revoked=revoked)

    @app.route("/share/revoke", methods=["POST"])
    def share_revoke():
        """Revoke a share by token."""
        token = request.form.get("token", "").strip()
        if not token:
            abort(400)
        db_path = app.config.get("DATABASE_PATH")
        if not db_path:
            abort(503)
        import share_store
        share_store.revoke(db_path, token)
        return redirect(url_for("share_result", token=token, revoked=1))


def _register_public_routes():
    """Register routes for mode=public: only GET /v/<token>."""

    @app.route("/v/<token>")
    def view_by_token(token):
        """Serve file by share token; no path from client."""
        db_path = app.config.get("DATABASE_PATH")
        if not db_path:
            abort(503)
        import share_store
        row = share_store.get_by_token(db_path, token)
        print(row)
        print(share_store.is_share_active(row))
        if not row or not share_store.is_share_active(row):
            abort(404)
        file_path = row["file_path"]
        root = app.config["MEDIA_ROOT"]
        resolved = resolve_under_root(root, file_path, must_be_file=True)
        if resolved is None or not resolved.is_file():
            abort(404)
        filename = _sanitize_unicode(resolved.name)
        stream_url = url_for("view_by_token", token=token)
        download_url = url_for("view_by_token", token=token, download=1)
        return serve_resolved_file(
            resolved, stream_url, download_url, filename,
            show_share=False, path_for_share="",
        )


if _MODE == "private":
    _register_private_routes()
else:
    _register_public_routes()
    # Public: optional catch-all 404 for /
    @app.route("/")
    def public_index():
        abort(404)


# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
