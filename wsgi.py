#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - Production WSGI Entry Point

Production-grade WSGI server using waitress.
Replaces Flask development server for production deployment.
"""

import os
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Load environment from .env
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Import Flask app
from web_app import app  # noqa: E402

# Validate production configuration
def validate_production_config():
    """Ensure production environment is properly configured."""
    env = os.environ.get('ACAS_ENV', os.environ.get('ENVIRONMENT', 'development'))
    
    if env in ('production', 'prod'):
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key or len(secret_key) < 32:
            raise ValueError(
                "FATAL: SECRET_KEY must be set and at least 32 characters in production!\n"
                "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\"\n"
                "Then add to .env: SECRET_KEY=<your-key>"
            )
        
        # Check for default/weak keys
        weak_keys = [
            'acas-pro-secret-key-change-me',
            'dev-key-change-in-production',
            'test-secret-key',
        ]
        if secret_key.lower() in weak_keys or any(w in secret_key.lower() for w in weak_keys):
            raise ValueError("FATAL: SECRET_KEY appears to be a default/weak key. Please generate a strong key.")
        
        print("✅ Production configuration validated")
    else:
        print(f"⚠️  Running in {env} mode (not production)")

if __name__ == "__main__":
    from waitress import serve
    
    # Validate configuration
    validate_production_config()
    
    # Server configuration
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '5000'))
    threads = int(os.environ.get('THREADS', '4'))
    connection_limit = int(os.environ.get('CONNECTION_LIMIT', '100'))
    
    print("🚀 Starting ACAS Pro production server...")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Threads: {threads}")
    print(f"   Connection Limit: {connection_limit}")
    print(f"   Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print()
    
    # Start server
    serve(
        app,
        host=host,
        port=port,
        threads=threads,
        connection_limit=connection_limit,
        channel_timeout=30,
        cleanup_interval=10,
        expose_tracebacks=False,  # Never expose tracebacks in production
    )
