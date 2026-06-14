#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WSGI server for E2E testing using waitress.

This provides a production-grade WSGI server that doesn't have
the single-threaded limitations of Flask's development server.
"""

import sys
import os
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import Flask app
from web_app import app  # noqa: E402

if __name__ == "__main__":
    from waitress import serve
    
    port = int(os.environ.get("FLASK_PORT", "5000"))
    
    print(f"Starting waitress WSGI server on port {port}...")
    serve(app, host="127.0.0.1", port=port, threads=4)
