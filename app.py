"""
Minimalist media browser: browse dirs under a configured root, stream video, display images.
Path traversal is prevented by resolving all paths under the configured media_root.
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


def get_media_root() -> Path:
    """Return the resolved media root path from config. Fails if missing or not a directory."""
    config = load_config(CONFIG_PATH)
    root = Path(config["media_root"]).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"media_root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"media_root is not a directory: {root}")
    return root


MEDIA_ROOT = get_media_root()

app = Flask(__name__)
app.config["MEDIA_ROOT"] = MEDIA_ROOT


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


def get_mime(path: Path) -> str | None:
    """Return MIME type for path by extension, or None if unknown."""
    ext = path.suffix.lower()
    if ext in VIDEO_MIME:
        return VIDEO_MIME[ext]
    if ext in IMAGE_MIME:
        return IMAGE_MIME[ext]
    return None


def is_video(path: Path) -> bool:
    """Return True if path has a known video extension."""
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_image(path: Path) -> bool:
    """Return True if path has a known image extension."""
    return path.suffix.lower() in IMAGE_EXTENSIONS


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------


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
    # List directory: dirs first, then files
    root = app.config["MEDIA_ROOT"]
    try:
        entries = sorted(
            list(resolved.iterdir()),
            key=lambda entry: (not entry.is_dir(), entry.name.lower()),
        )
    except OSError:
        abort(404)
    # Relative path for links
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


def redirect_to_view(rel_path: str):
    """Redirect to the view route for the given relative path."""
    return redirect(url_for("view", path=rel_path))


@app.route("/view")
def view():
    """Stream video/image file or return viewer HTML depending on Accept/embed."""
    raw = request.args.get("path", "").strip()
    resolved = resolve_safe(raw, must_be_file=True)
    if resolved is None:
        abort(403)
    if not resolved.is_file():
        abort(404)
    # Optional: if client wants HTML (e.g. Accept or ?embed=1), return viewer page
    embed = request.args.get("embed", "").lower() in ("1", "true", "yes")
    if embed or "text/html" in request.headers.get("Accept", ""):
        path_safe = _sanitize_unicode(raw)
        if is_video(resolved):
            return render_template("view_video.html", path=path_safe)
        if is_image(resolved):
            return render_template("view_image.html", path=path_safe)
    # Otherwise stream/send file
    mime = get_mime(resolved)
    if not mime:
        abort(404)
    if is_video(resolved):
        return send_file(
            resolved,
            mimetype=mime,
            conditional=True,
            as_attachment=False,
        )
    return send_file(resolved, mimetype=mime, as_attachment=False)


# -----------------------------------------------------------------------------
# Entry
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
