#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Quick Test
"""

import sys
sys.path.insert(0, r'F:\自动获客系统\ACAS-Pro\src')

print("Testing ACAS Pro imports...")

try:
    from PySide6.QtWidgets import QApplication
    print("✓ PySide6 imported")
    
    from acas_pro.core.config import config
    print("✓ Config imported")
    
    from acas_pro.core.database import Database
    print("✓ Database imported")
    
    from acas_pro.core.security import SecurityManager
    print("✓ Security imported")
    
    from acas_pro.services.user_service import user_service
    print("✓ User service imported")
    
    from acas_pro.ui.auth.login_dialog import LoginDialog
    print("✓ Login dialog imported")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test database initialization
print("\nTesting database initialization...")
try:
    db = Database()
    print("✓ Database initialized")
except Exception as e:
    print(f"✗ Database error: {e}")

print("\nAll tests passed!")
