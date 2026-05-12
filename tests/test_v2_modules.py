#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2 module coverage tests"""

import pytest


class TestV2Modules:
    """Test v2 modules"""
    
    def test_ad_manager_v2(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        assert AdManager is not None
    
    def test_database_v2(self):
        from acas_pro.core.database_v2 import DatabaseManager
        db = DatabaseManager()
        assert db is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
