#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Updater Unit Tests
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from acas_pro.update.updater import (
    UpdateChecker, UpdateInfo, check_for_updates, download_update
)


class TestUpdateInfo:
    def test_update_info_creation(self):
        info = UpdateInfo(
            version="5.2.0",
            release_date="2024-01-01",
            download_url="https://example.com/update.exe",
            sha256="abc123",
            changelog="New features",
            mandatory=True
        )
        assert info.version == "5.2.0"
        assert info.mandatory is True


class TestUpdateChecker:
    @pytest.fixture
    def checker(self):
        return UpdateChecker(current_version="5.1.0")

    def test_init(self, checker):
        assert checker.current_version == "5.1.0"
        assert checker._update_info is None

    def test_compare_versions_equal(self, checker):
        assert checker._compare_versions("5.1.0", "5.1.0") == 0

    def test_compare_versions_greater(self, checker):
        assert checker._compare_versions("5.2.0", "5.1.0") > 0

    def test_compare_versions_less(self, checker):
        assert checker._compare_versions("5.0.0", "5.1.0") < 0

    def test_compare_versions_with_v_prefix(self, checker):
        assert checker._compare_versions("v5.2.0", "5.1.0") > 0

    def test_compare_versions_different_length(self, checker):
        assert checker._compare_versions("5.1.0.1", "5.1.0") > 0

    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_check_no_update(self, mock_request, mock_urlopen, checker):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"latest_version": "5.1.0"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        has_update, info = checker.check()

        assert has_update is False
        assert info is None

    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_check_has_update(self, mock_request, mock_urlopen, checker):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"latest_version": "5.2.0", "release_date": "2024-01-01", "download_url": "http://example.com/update.exe", "sha256": "abc123", "changelog": "New features"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        has_update, info = checker.check()

        assert has_update is True
        assert info is not None
        assert info.version == "5.2.0"

    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_check_network_error(self, mock_request, mock_urlopen, checker):
        mock_urlopen.side_effect = Exception("Network error")

        has_update, info = checker.check()

        assert has_update is False
        assert info is None

    def test_get_update_info_none(self, checker):
        assert checker.get_update_info() is None

    def test_get_update_info_exists(self, checker):
        checker._update_info = UpdateInfo(
            version="5.2.0",
            release_date="2024-01-01",
            download_url="http://example.com/update.exe",
            sha256="abc123",
            changelog="New features"
        )
        info = checker.get_update_info()
        assert info.version == "5.2.0"

    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', MagicMock())
    @patch('hashlib.sha256')
    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_download_success(self, mock_request, mock_urlopen, mock_sha256, mock_mkdir, checker):
        # Setup update info
        checker._update_info = UpdateInfo(
            version="5.2.0",
            release_date="2024-01-01",
            download_url="http://example.com/update.exe",
            sha256="",
            changelog="New features"
        )

        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {"Content-Length": "100"}
        mock_response.read.side_effect = [b'x' * 50, b'x' * 50, b'']
        mock_urlopen.return_value.__enter__.return_value = mock_response

        progress_calls = []
        result = checker.download(progress_callback=lambda p: progress_calls.append(p))

        assert result is not None

    def test_download_no_update_info(self, checker):
        result = checker.download()
        assert result is None

    @patch('urllib.request.urlopen')
    @patch('urllib.request.Request')
    def test_download_network_error(self, mock_request, mock_urlopen, checker):
        checker._update_info = UpdateInfo(
            version="5.2.0",
            release_date="2024-01-01",
            download_url="http://example.com/update.exe",
            sha256="abc123",
            changelog="New features"
        )
        mock_urlopen.side_effect = Exception("Network error")

        result = checker.download()

        assert result is None


class TestGlobalFunctions:
    @patch('acas_pro.update.updater._checker.check')
    def test_check_for_updates(self, mock_check):
        mock_check.return_value = (True, None)
        result = check_for_updates()
        assert result == (True, None)

    @patch('acas_pro.update.updater._checker.download')
    def test_download_update(self, mock_download):
        mock_download.return_value = Path("/tmp/update.exe")
        result = download_update()
        assert result == Path("/tmp/update.exe")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
