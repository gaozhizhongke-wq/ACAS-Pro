#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Update Module Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from acas_pro.update.updater import UpdateChecker, UpdateInfo, check_for_updates, download_update


class TestUpdateInfo:
    """Update info dataclass tests"""
    
    def test_update_info_creation(self):
        """Test update info creation"""
        info = UpdateInfo(
            version="5.2.0",
            release_date="2026-05-01",
            download_url="https://example.com/update.exe",
            sha256="abc123",
            changelog="New features",
            mandatory=True
        )
        
        assert info.version == "5.2.0"
        assert info.mandatory is True


class TestUpdateChecker:
    """Update checker tests"""
    
    @pytest.fixture
    def checker(self):
        return UpdateChecker(current_version="5.1.0")
    
    def test_init(self, checker):
        """Test initialization"""
        assert checker.current_version == "5.1.0"
        assert checker._update_info is None
    
    def test_compare_versions_equal(self, checker):
        """Test version comparison - equal"""
        result = checker._compare_versions("5.1.0", "5.1.0")
        assert result == 0
    
    def test_compare_versions_greater(self, checker):
        """Test version comparison - greater"""
        result = checker._compare_versions("5.2.0", "5.1.0")
        assert result > 0
    
    def test_compare_versions_less(self, checker):
        """Test version comparison - less"""
        result = checker._compare_versions("5.0.0", "5.1.0")
        assert result < 0
    
    def test_compare_versions_with_v_prefix(self, checker):
        """Test version comparison with v prefix"""
        result = checker._compare_versions("v5.2.0", "5.1.0")
        assert result > 0
    
    def test_compare_versions_different_length(self, checker):
        """Test version comparison with different lengths"""
        result = checker._compare_versions("5.1.1", "5.1.0")
        assert result > 0
    
    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_check_no_update(self, mock_request, mock_urlopen, checker):
        """Test check when no update available"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"latest_version": "5.1.0"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        has_update, info = checker.check()
        
        assert has_update is False
        assert info is None
    
    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_check_has_update(self, mock_request, mock_urlopen, checker):
        """Test check when update available"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'''{
            "latest_version": "5.2.0",
            "release_date": "2026-05-01",
            "download_url": "https://example.com/update.exe",
            "sha256": "abc123",
            "changelog": "New features"
        }'''
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        has_update, info = checker.check()
        
        assert has_update is True
        assert info is not None
        assert info.version == "5.2.0"
    
    @patch('urllib.request.urlopen')
    def test_check_network_error(self, mock_urlopen, checker):
        """Test check with network error"""
        mock_urlopen.side_effect = Exception("Network error")
        
        has_update, info = checker.check()
        
        assert has_update is False
        assert info is None
    
    def test_get_update_info_none(self, checker):
        """Test get update info when none available"""
        info = checker.get_update_info()
        assert info is None
    
    def test_get_update_info_exists(self, checker):
        """Test get update info when available"""
        checker._update_info = UpdateInfo(
            version="5.2.0",
            release_date="2026-05-01",
            download_url="https://example.com/update.exe",
            sha256="abc123",
            changelog="New features"
        )
        
        info = checker.get_update_info()
        assert info is not None
        assert info.version == "5.2.0"


class TestGlobalFunctions:
    """Global function tests"""
    
    @patch('acas_pro.update.updater._checker')
    def test_check_for_updates(self, mock_checker):
        """Test global check function"""
        mock_checker.check.return_value = (True, None)
        
        result = check_for_updates()
        
        assert result == (True, None)
        mock_checker.check.assert_called_once()
    
    @patch('acas_pro.update.updater._checker')
    def test_download_update(self, mock_checker):
        """Test global download function"""
        mock_checker.download.return_value = Path("/tmp/update.exe")
        
        result = download_update()
        
        assert result == Path("/tmp/update.exe")
        mock_checker.download.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
