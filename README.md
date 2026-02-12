# Media player – browse and stream

[![Tests](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml/badge.svg)](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml)
[![Pylint](https://img.shields.io/badge/pylint-10%2F10-brightgreen)](https://github.com/chervaliery/MediaPlayer/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/chervaliery/MediaPlayer/graph/badge.svg)](https://codecov.io/gh/chervaliery/MediaPlayer)
[![CodeQL](https://github.com/chervaliery/MediaPlayer/actions/workflows/codeql.yml/badge.svg)](https://github.com/chervaliery/MediaPlayer/actions/workflows/codeql.yml)

Minimal Python web app to browse a configured directory and stream MKV (or other) video and display images in the browser.

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

## Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

## Configuration

- **Config file**: by default `config.yaml` in the project directory. Override with the `PLAYER_CONFIG` environment variable (path to a YAML file with `media_root`).
