"""WSGI entry point for Apache mod_wsgi."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

application = app

application = app
