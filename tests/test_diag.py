"""Minimal diagnostic: just import test_api and check jwt_manager state"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

def test_diagnostic_jwt():
    """Check if jwt_manager works at this point"""
    from acas_pro.core.security import jwt_manager
    from acas_pro.core.config import get_config
    from unittest.mock import MagicMock
    
    cfg = get_config()
    print(f"\n_config_instance type: {type(cfg).__name__}")
    print(f"security.jwt_algorithm: {cfg.security.jwt_algorithm!r}")
    print(f"is MagicMock: {isinstance(cfg.security.jwt_algorithm, MagicMock)}")
    
    try:
        token = jwt_manager.generate_token("test_user")
        print(f"generate_token OK: {token[:30]}...")
    except Exception as e:
        print(f"generate_token FAILED: {e}")
        import traceback
        traceback.print_exc()
