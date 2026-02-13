# Media player – browse and stream

[![Tests](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml/badge.svg)](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml)
[![Pylint](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/chervaliery/MediaPlayer/main/badges/pylint.json)](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/chervaliery/MediaPlayer/graph/badge.svg)](https://codecov.io/gh/chervaliery/MediaPlayer)
[![CodeQL](https://github.com/chervaliery/MediaPlayer/actions/workflows/codeql.yml/badge.svg)](https://github.com/chervaliery/MediaPlayer/actions/workflows/codeql.yml)

Minimal Python web app to browse a configured directory and stream MKV (or other) video and display images in the browser.

## Features

- **Browse and stream:** Browse directories under a configured root; view or stream video, images, and audio; display text files; download any file.
- **Sharing:** Two modes in one codebase.
  - **Private mode** (`mode: private`): Full browse and view by path. A Share button on file views opens a form (expiration: default / custom / never); creating a link reuses an existing active share for the same file or creates a new one. The result page shows the public URL with copy and revoke.
  - **Public mode** (`mode: public`): No browse; only **GET /v/\<token\>** to view or download by share token (no path in the URL).
  Same SQLite database and `media_root` for both processes; route by host (e.g. private.example.com vs public.example.com).

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Edit `config.yaml` and set `media_root` to your media directory (must exist and be a directory):

   ```yaml
   media_root: /var/media
   ```

## Run locally

```bash
source venv/bin/activate
python app.py
```

Then open http://127.0.0.1:5000/

## Deploy with Apache mod_wsgi

The app runs inside Apache using mod_wsgi. Authentication is handled by Apache (e.g. `mod_auth_*`); the app does not implement auth.

1. Install mod_wsgi (Ubuntu/Debian):

   ```bash
   sudo apt install libapache2-mod-wsgi-py3
   sudo a2enmod wsgi
   ```

2. Copy or symlink the project to a directory Apache can read (e.g. `/var/www/player`). Use a virtual environment and install dependencies there.

3. Add a site or drop-in config. Example for serving the app at the root of a virtual host:

   ```apache
   WSGIDaemonProcess player user=www-data group=www-data python-home=/var/www/player/venv
   WSGIProcessGroup player
   WSGIScriptAlias / /var/www/player/wsgi.py

   <Directory /var/www/player>
       Require all granted
   </Directory>
   ```

   Adjust paths to match your setup. To mount the app under a subpath (e.g. `/media`), use:

   ```apache
   WSGIScriptAlias /media /var/www/player/wsgi.py
   ```

   Then configure auth for the same location as needed.

4. Restart Apache:

   ```bash
   sudo systemctl restart apache2
   ```

5. Config: put `config.yaml` in the project directory with `media_root` set, or point to another config file with `SetEnv PLAYER_CONFIG /etc/player/config.yaml` in the same Apache context.

### Two-process deployment (sharing)

To enable share links you run two WSGI processes (or two vhosts): one with `mode=private`, one with `mode=public`.

- Use the **same** `database` path and **same** `media_root` in both configs (only `mode` and optionally `public_base_url` differ).
- Point the private host (e.g. `private.example.com`) to the private process and the public host (e.g. `public.example.com`) to the public process. Use Apache or Nginx to proxy by host; each app can be served at the root of its host.
- The private process reads and writes the SQLite DB (create share, revoke). The public process only reads the DB and serves files under `media_root`.
- See [docs/PLAN_PRIVATE_PUBLIC_SHARING.md](docs/PLAN_PRIVATE_PUBLIC_SHARING.md) for the architecture.

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

**Test layout:**

- `test_config.py` – config file loading
- `test_config_validation.py` – config validation (mode, database, share_default_expiry_seconds)
- `test_helpers.py` – MIME and file-type helpers
- `test_resolve.py` – path resolution under media root
- `test_routes.py` – browse and path-based view routes
- `test_share_routes.py` – share routes and public token view (GET /v/\<token\>)
- `test_share_store.py` – SQLite share store (create, get, revoke, get_active_by_file_path)

## Configuration

- **Config file:** Default `config.yaml` in the project directory. Override with the `PLAYER_CONFIG` environment variable (path to a YAML file).
- **Keys:**
  - `mode` – `private` or `public` (which routes are enabled)
  - `media_root` – path to the media directory (must exist)
  - `database` – path to the SQLite file for share links (same path for both private and public processes)
  - `share_default_expiry_seconds` – default TTL for new share links (e.g. 86400 = 24h); required when `mode` is private and `database` is set
  - `public_base_url` – base URL of the public app (e.g. `https://public.example.com`) for building share links in the private app

When `mode` is public, `database` is required. When `mode` is private and `database` is set, `share_default_expiry_seconds` is required.
