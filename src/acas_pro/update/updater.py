# -*- coding: utf-8 -*-
"""
ACAS Pro - Auto Update System
Check for updates, download, and install
"""

import json
import sqlite3
import hashlib
from acas_pro.core.logging import get_logger
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
import asyncio

# Try importing aiohttp for async HTTP
try:
    import aiohttp

    _HAS_AIOHTTP = True
except ImportError:
    _HAS_AIOHTTP = False


def _safe_urlopen(req, **kwargs):
    """Validate URL scheme before opening (http/https only)."""
    url = req.full_url if hasattr(req, "full_url") else str(req)
    scheme = urllib.parse.urlparse(url).scheme
    if scheme not in ("http", "https"):
        raise ValueError(
            f"Unsupported URL scheme: {scheme!r} (only http/https allowed)"
        )
    return urllib.request.urlopen(req, **kwargs)  # nosec B310  # validated scheme above


logger = get_logger(__name__)


@dataclass
class UpdateInfo:
    """更新信息"""

    version: str
    release_date: str
    download_url: str
    sha256: str
    changelog: str
    mandatory: bool = False


class UpdateChecker:
    """更新检查器"""

    # 更新检查URL（可替换为实际服务器）
    UPDATE_URL = "https://api.acas-pro.com/update/check"
    VERSION_FILE = "https://acas-pro.com/releases/version.json"

    def __init__(self, current_version: str = "5.1.0"):
        self.current_version = current_version
        self._update_info: Optional[UpdateInfo] = None

    def check(self) -> Tuple[bool, Optional[UpdateInfo]]:
        """检查是否有更新"""
        try:
            req = urllib.request.Request(
                self.VERSION_FILE,
                headers={"User-Agent": f"ACAS-Pro/{self.current_version}"},
            )
            with _safe_urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            latest = data.get("latest_version", self.current_version)
            if self._compare_versions(latest, self.current_version) > 0:
                self._update_info = UpdateInfo(
                    version=latest,
                    release_date=data.get("release_date", ""),
                    download_url=data.get("download_url", ""),
                    sha256=data.get("sha256", ""),
                    changelog=data.get("changelog", "Bug fixes and improvements"),
                    mandatory=data.get("mandatory", False),
                )
                return True, self._update_info
            return False, None

        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            TypeError,
            OSError,
            urllib.error.URLError,
        ) as e:
            logger.exception(f"Error in check: {e}")
            return False, None

    async def check_async(self) -> Tuple[bool, Optional[UpdateInfo]]:
        """检查是否有更新 (异步版本)"""
        if not _HAS_AIOHTTP:
            # Fallback to threaded sync version
            return await asyncio.to_thread(self.check)

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.VERSION_FILE) as response:
                    data = await response.json()

            latest = data.get("latest_version", self.current_version)
            if self._compare_versions(latest, self.current_version) > 0:
                self._update_info = UpdateInfo(
                    version=latest,
                    release_date=data.get("release_date", ""),
                    download_url=data.get("download_url", ""),
                    sha256=data.get("sha256", ""),
                    changelog=data.get("changelog", "Bug fixes and improvements"),
                    mandatory=data.get("mandatory", False),
                )
                return True, self._update_info
            return False, None

        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            OSError,
            urllib.error.URLError,
        ) as e:
            logger.exception(f"Error in check_async: {e}")
            return False, None

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，返回 >0 表示 v1>v2"""

        def parse(v) -> None:
            parts = v.replace("v", "").split(".")
            return [int(p) for p in parts if p.isdigit()]

        p1, p2 = parse(v1), parse(v2)
        for a, b in zip(p1, p2):
            if a != b:
                return a - b
        return len(p1) - len(p2)

    def download(
        self, progress_callback: Optional[Callable[[int], None]] = None
    ) -> Optional[Path]:
        """下载更新"""
        if not self._update_info:
            return None

        try:
            download_dir = Path.home() / ".acas-pro" / "updates"
            download_dir.mkdir(parents=True, exist_ok=True)

            filename = f"ACAS-Pro-{self._update_info.version}-setup.exe"
            filepath = download_dir / filename

            req = urllib.request.Request(
                self._update_info.download_url,
                headers={"User-Agent": f"ACAS-Pro/{self.current_version}"},
            )

            with _safe_urlopen(req, timeout=30) as response:
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                chunk_size = 8192

                with open(filepath, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total:
                            progress_callback(int(downloaded * 100 / total))

            # 验证哈希
            if self._update_info.sha256:
                sha256 = hashlib.sha256(filepath.read_bytes()).hexdigest()
                if sha256 != self._update_info.sha256.lower():
                    filepath.unlink()
                    return None

            return filepath

        except (
            sqlite3.Error,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
            TypeError,
            OSError,
        ) as e:
            logger.exception(f"Error in download: {e}")
            return None

    def get_update_info(self) -> Optional[UpdateInfo]:
        """获取更新信息"""
        return self._update_info


# 全局实例
_checker = UpdateChecker()


def check_for_updates() -> Tuple[bool, Optional[UpdateInfo]]:
    """检查更新"""
    return _checker.check()


def download_update(
    progress_callback: Optional[Callable[[int], None]] = None,
) -> Optional[Path]:
    """下载更新"""
    return _checker.download(progress_callback)
