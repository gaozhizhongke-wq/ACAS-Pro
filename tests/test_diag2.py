"""Diagnostic: check security._cfg() directly"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

def test_diagnostic_jwt_deep():
    from acas_pro.core.security import jwt_manager, _cfg, get_config
    from acas_pro.core.config import get_config as cfg_get_config, _config_instance
    from unittest.mock import MagicMock
    
    # Check all possible paths to config
    print(f"\n=== DIAGNOSTIC ===")
    
    # 1. Direct get_config from config module
    c1 = cfg_get_config()
    print(f"cfg_get_config().security.jwt_algorithm = {c1.security.jwt_algorithm!r}")
    
    # 2. _config_instance 
    if _config_instance is not None:
        print(f"_config_instance.security.jwt_algorithm = {_config_instance.security.jwt_algorithm!r}")
    
    # 3. security module's get_config
    print(f"security.get_config is cfg.get_config: {get_config is cfg_get_config}")
    c2 = get_config()
    print(f"security.get_config().security.jwt_algorithm = {c2.security.jwt_algorithm!r}")
    
    # 4. security._cfg()
    c3 = _cfg()
    print(f"security._cfg().security.jwt_algorithm = {c3.security.jwt_algorithm!r}")
    print(f"is MagicMock: {isinstance(c3.security.jwt_algorithm, MagicMock)}")
    
    # 5. Now check what jwt.encode gets
    print(f"\n--- Trying generate_token ---")
    import jwt
    payload = {'sub': 'test', 'iat': 1, 'exp': 9999999999}
    
    # Get what _cfg() returns RIGHT NOW
    cfg = _cfg()
    alg = cfg.security.jwt_algorithm
    print(f"alg = {alg!r} (type={type(alg).__name__})")
    
    # Try encoding manually
    try:
        key = jwt_manager._get_secret_key()
        print(f"key type: {type(key).__name__}")
        token = jwt.encode(payload, key, algorithm=alg)
        print(f"jwt.encode OK: {token[:30]}...")
    except Exception as e:
        print(f"jwt.encode FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Check if security module's get_config is a MagicMock
    import acas_pro.core.security as sec_mod
    print(f"\n--- Module introspection ---")
    print(f"sec_mod._cfg.__globals__['get_config'] is cfg_get_config: {sec_mod._cfg.__globals__['get_config'] is cfg_get_config}")
    gc_in_sec = sec_mod._cfg.__globals__['get_config']
    print(f"sec_mod._cfg.__globals__['get_config'] = {gc_in_sec}")
    print(f"is MagicMock: {isinstance(gc_in_sec, MagicMock)}")
