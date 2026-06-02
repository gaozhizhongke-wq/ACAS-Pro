# -*- coding: utf-8 -*-
"""
ACAS Pro - Auto Update System
Check for updates, download, and install
"""

import json
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


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
                headers={"User-Agent": f"ACAS-Pro/{self.current_version}"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            latest = data.get("latest_version", self.current_version)
            if self._compare_versions(latest, self.current_version) > 0:
                self._update_info = UpdateInfo(
                    version=latest,
                    release_date=data.get("release_date", ""),
                    download_url=data.get("download_url", ""),
                    sha256=data.get("sha256", ""),
                    changelog=data.get("changelog", "Bug fixes and improvements"),
                    mandatory=data.get("mandatory", False)
                )
                return True, self._update_info
            return False, None

        except Exception as e:
            logger.exception(f"Error in unknown_function: {e}")
            return False, None

    def _compare_versions(self, v1: str, v2: str) -> int:
        """比较版本号，返回 >0 表示 v1>v2"""
        def parse(v):
            parts = v.replace("v", "").split(".")
            return [int(p) for p in parts if p.isdigit()]

        p1, p2 = parse(v1), parse(v2)
        for a, b in zip(p1, p2):
            if a != b:
                return a - b
        return len(p1) - len(p2)

    def download(self, progress_callback: Optional[Callable[[int], None]] = None) -> Optional[Path]:
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
                headers={"User-Agent": f"ACAS-Pro/{self.current_version}"}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
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

        except Exception as e:
            logger.exception(f"Error in unknown_function: {e}")
            return None

    def get_update_info(self) -> Optional[UpdateInfo]:
        """获取更新信息"""
        return self._update_info


# 全局实例
_checker = UpdateChecker()

def check_for_updates() -> Tuple[bool, Optional[UpdateInfo]]:
    """检查更新"""
    return _checker.check()

def download_update(progress_callback: Optional[Callable[[int], None]] = None) -> Optional[Path]:
    """下载更新"""
    return _checker.download(progress_callback)
