#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro Playwright E2E Test Configuration

Sets up Flask server for E2E testing.
pytest-playwright provides browser fixtures automatically.
"""

import pytest
import subprocess
import sys
import os
import time
import signal
import requests
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"{url}/api/health", timeout=2)
            if resp.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.5)
    return False


@pytest.fixture(scope="session")
def flask_server():
    """Start Flask server for E2E tests session."""
    port = 5000  # web_app.py hardcodes port 5000
    base_url = f"http://127.0.0.1:{port}"
    
    # Check if server already running
    try:
        resp = requests.get(f"{base_url}/api/health", timeout=2)
        if resp.status_code == 200:
            yield base_url
            return
    except requests.exceptions.RequestException:
        pass
    
    # Set environment
    env = os.environ.copy()
    env["FLASK_ENV"] = "testing"
    env["SECRET_KEY"] = "test-secret-key-for-e2e-testing-only-not-for-production"
    env["ENVIRONMENT"] = "testing"
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    
    # Start server using waitress (production WSGI) instead of Flask dev server
    wsgi_path = PROJECT_ROOT / "wsgi_server.py"
    proc = subprocess.Popen(
        [sys.executable, str(wsgi_path)],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
    )
    
    # Wait for server
    if not wait_for_server(base_url, timeout=30):
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        pytest.skip("Flask server failed to start")
    
    yield base_url
    
    # Cleanup
    if os.name == 'nt':
        proc.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# pytest-playwright automatically provides:
# - page: Page fixture (browser context page)
# - browser: Browser fixture
# - context: BrowserContext fixture
# - browser_type_launch_args: launch args
# - browser_context_args: context args
#
# We need to configure the base_url for tests
@pytest.fixture(scope="session")
def base_url(flask_server):
    """Base URL for the Flask server."""
    return flask_server


@pytest.fixture(scope="function")
def authenticated_page(page, flask_server: str):
    """Page with auth token pre-injected to bypass login overlay."""
    # Generate a test token (matches JWT format expected by web_app.py)
    import jwt
    from datetime import datetime, timedelta, timezone
    
    # Create a test JWT token
    test_payload = {
        'user_id': 'test-user-e2e',
        'account': 'test_e2e@acas.local',
        'exp': datetime.now(timezone.utc) + timedelta(hours=24),
        'iat': datetime.now(timezone.utc),
    }
    test_secret = 'test-secret-key-for-e2e-testing-only-not-for-production'
    test_token = jwt.encode(test_payload, test_secret, algorithm='HS256')
    
    # Inject token into localStorage before page loads
    page.add_init_script(f"""
        localStorage.setItem('acas_token', '{test_token}');
    """)
    
    yield page
