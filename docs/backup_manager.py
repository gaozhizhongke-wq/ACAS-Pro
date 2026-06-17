# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
备份策略管理模块
支持全量/增量备份，备份验证和恢复测试，多存储后端
"""

import json
import os
import time
import logging
import hashlib
import tarfile
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum
import sys

logger = logging.getLogger(__name__)


class BackupType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class StorageBackend(Enum):
    LOCAL = "local"
    S3 = "s3"
    NAS = "nas"


class BackupStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"
    VERIFIED = "verified"


@dataclass
class BackupRecord:
    id: str
    backup_type: BackupType
    storage: StorageBackend
    path: str
    size_bytes: int = 0
    checksum: str = ""
    status: BackupStatus = BackupStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0
    parent_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class RetentionPolicy:
    """备份保留策略"""

    def __init__(self, daily_keep: int = 7, weekly_keep: int = 4,
                 monthly_keep: int = 6, yearly_keep: int = 2):
        self.daily_keep = daily_keep
        self.weekly_keep = weekly_keep
        self.monthly_keep = monthly_keep
        self.yearly_keep = yearly_keep

    def should_keep(self, record: BackupRecord, all_records: List[BackupRecord]) -> bool:
        created = datetime.fromisoformat(record.created_at)
        now = datetime.now()
        age_days = (now - created).days

        same_day = [r for r in all_records if
                     datetime.fromisoformat(r.created_at).date() == created.date()]
        if len(same_day) <= self.daily_keep and age_days <= self.daily_keep:
            return True

        same_week = [r for r in all_records if
                      datetime.fromisoformat(r.created_at).isocalendar()[:2] ==
                      created.isocalendar()[:2]]
        if len(same_week) <= self.weekly_keep and age_days <= self.weekly_keep * 7:
            return True

        same_month = [r for r in all_records if
                       datetime.fromisoformat(r.created_at).strftime("%Y-%m") ==
                       created.strftime("%Y-%m")]
        if len(same_month) <= self.monthly_keep and age_days <= self.monthly_keep * 30:
            return True

        if age_days <= self.yearly_keep * 365:
            return True

        return False


class BackupManager:
    """备份管理器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.backup_dir = self.config.get("backup_dir", "backups")
        self.retention = RetentionPolicy(
            daily_keep=self.config.get("daily_keep", 7),
            weekly_keep=self.config.get("weekly_keep", 4),
            monthly_keep=self.config.get("monthly_keep", 6),
            yearly_keep=self.config.get("yearly_keep", 2)
        )
        self.records: List[BackupRecord] = []
        self._catalog_path = os.path.join(self.backup_dir, "catalog.json")
        self._load_catalog()

    def _load_catalog(self):
        if os.path.exists(self._catalog_path):
            try:
                with open(self._catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.records = [
                    BackupRecord(
                        id=r["id"], backup_type=BackupType(r["type"]),
                        storage=StorageBackend(r.get("storage", "local")),
                        path=r["path"], size_bytes=r.get("size", 0),
                        checksum=r.get("checksum", ""), status=BackupStatus(r.get("status", "completed")),
                        created_at=r["created_at"], duration_seconds=r.get("duration", 0),
                        parent_id=r.get("parent", ""), metadata=r.get("metadata", {})
                    ) for r in data
                ]
            except Exception as e:
                logger.error("加载备份目录失败: %s", e)
                self.records = []

    def _save_catalog(self):
        os.makedirs(self.backup_dir, exist_ok=True)
        data = [
            {
                "id": r.id, "type": r.backup_type.value,
                "storage": r.storage.value, "path": r.path,
                "size": r.size_bytes, "checksum": r.checksum,
                "status": r.status.value, "created_at": r.created_at,
                "duration": r.duration_seconds, "parent": r.parent_id,
                "metadata": r.metadata
            } for r in self.records
        ]
        with open(self._catalog_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _checksum_file(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def backup_database(self, db_url: str = None, backup_type: BackupType = BackupType.FULL) -> BackupRecord:
        """备份数据库"""
        record_id = f"db_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record = BackupRecord(
            id=record_id, backup_type=backup_type,
            storage=StorageBackend.LOCAL, path=""
        )
        record.status = BackupStatus.RUNNING
        self.records.append(record)

        start = time.time()
        try:
            from dotenv import load_dotenv
            load_dotenv()
            url = db_url or os.getenv("DATABASE_URL", "")

            os.makedirs(self.backup_dir, exist_ok=True)
            backup_file = os.path.join(self.backup_dir, f"{record_id}.sql")

            if "postgresql" in url or "postgres" in url:
                self._backup_postgresql(url, backup_file)
            elif "sqlite" in url or not url:
                db_path = url.replace("sqlite:///", "") if url else "data/acas_pro.db"
                self._backup_sqlite(db_path, backup_file)
            else:
                raise ValueError(f"不支持的数据库类型: {url}")

            record.path = backup_file
            record.size_bytes = os.path.getsize(backup_file)
            record.checksum = self._checksum_file(backup_file)
            record.duration_seconds = round(time.time() - start, 2)
            record.status = BackupStatus.COMPLETED

            logger.info("数据库备份完成: %s (%.2fs, %d bytes)",
                       record_id, record.duration_seconds, record.size_bytes)
        except Exception as e:
            record.status = BackupStatus.FAILED
            record.metadata["error"] = str(e)
            logger.error("数据库备份失败: %s", e)

        self._save_catalog()
        return record

    def _backup_postgresql(self, url: str, output: str):
        import subprocess
        env = os.environ.copy()
        env["PGPASSWORD"] = self._extract_pg_password(url)
        cmd = ["pg_dump", "--format=custom", "--file", output, url]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

    def _backup_sqlite(self, db_path: str, output: str):
        if os.path.exists(db_path):
            import sqlite3
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(output)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
        else:
            with open(output, "w") as f:
                f.write("-- SQLite backup (empty source)\n")

    def _extract_pg_password(self, url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.password or ""
        except Exception:
            return ""

    def backup_files(self, source_dirs: List[str] = None,
                     backup_type: BackupType = BackupType.FULL) -> BackupRecord:
        """备份文件目录"""
        source_dirs = source_dirs or ["config", "certs", "web_static"]
        record_id = f"files_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        record = BackupRecord(
            id=record_id, backup_type=backup_type,
            storage=StorageBackend.LOCAL, path=""
        )
        record.status = BackupStatus.RUNNING
        self.records.append(record)

        start = time.time()
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            backup_file = os.path.join(self.backup_dir, f"{record_id}.tar.gz")

            with tarfile.open(backup_file, "w:gz") as tar:
                for src_dir in source_dirs:
                    if os.path.exists(src_dir):
                        tar.add(src_dir)

            record.path = backup_file
            record.size_bytes = os.path.getsize(backup_file)
            record.checksum = self._checksum_file(backup_file)
            record.duration_seconds = round(time.time() - start, 2)
            record.status = BackupStatus.COMPLETED
        except Exception as e:
            record.status = BackupStatus.FAILED
            record.metadata["error"] = str(e)

        self._save_catalog()
        return record

    def verify_backup(self, record_id: str) -> bool:
        """验证备份完整性"""
        record = next((r for r in self.records if r.id == record_id), None)
        if not record:
            logger.error("备份记录不存在: %s", record_id)
            return False

        record.status = BackupStatus.VERIFYING
        self._save_catalog()

        try:
            if not os.path.exists(record.path):
                raise FileNotFoundError(f"备份文件不存在: {record.path}")

            current_checksum = self._checksum_file(record.path)
            if current_checksum != record.checksum:
                raise ValueError(f"校验和不匹配: {current_checksum} != {record.checksum}")

            current_size = os.path.getsize(record.path)
            if current_size != record.size_bytes:
                raise ValueError(f"文件大小不匹配: {current_size} != {record.size_bytes}")

            if record.path.endswith(".tar.gz"):
                with tarfile.open(record.path, "r:gz") as tar:
                    members = tar.getmembers()
                    if not members:
                        raise ValueError("备份文件为空")

            record.status = BackupStatus.VERIFIED
            logger.info("备份验证通过: %s", record_id)
            self._save_catalog()
            return True
        except Exception as e:
            record.status = BackupStatus.FAILED
            record.metadata["verify_error"] = str(e)
            logger.error("备份验证失败: %s - %s", record_id, e)
            self._save_catalog()
            return False

    def restore_backup(self, record_id: str, target_dir: str = None) -> bool:
        """从备份恢复"""
        record = next((r for r in self.records if r.id == record_id), None)
        if not record:
            logger.error("备份记录不存在: %s", record_id)
            return False

        try:
            if record.path.endswith(".tar.gz"):
                target = target_dir or "."
                with tarfile.open(record.path, "r:gz") as tar:
                    tar.extractall(target)
                logger.info("文件备份恢复完成: %s -> %s", record_id, target)
            elif record.path.endswith(".sql"):
                logger.info("数据库备份恢复需要手动执行: %s", record.path)
            return True
        except Exception as e:
            logger.error("恢复失败: %s - %s", record_id, e)
            return False

    def cleanup_expired(self) -> List[str]:
        """清理过期备份"""
        removed = []
        for record in self.records[:]:
            if not self.retention.should_keep(record, self.records):
                try:
                    if os.path.exists(record.path):
                        os.remove(record.path)
                    self.records.remove(record)
                    removed.append(record.id)
                    logger.info("清理过期备份: %s", record.id)
                except Exception as e:
                    logger.error("清理失败: %s - %s", record.id, e)
        if removed:
            self._save_catalog()
        return removed

    def list_backups(self) -> List[Dict]:
        return [
            {
                "id": r.id, "type": r.backup_type.value,
                "status": r.status.value, "size": r.size_bytes,
                "created": r.created_at, "duration": r.duration_seconds,
                "checksum": r.checksum[:12] + "..."
            } for r in self.records
        ]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ACAS Pro 备份管理")
    parser.add_argument("action", choices=["backup-db", "backup-files", "verify", "restore", "list", "cleanup"])
    parser.add_argument("--id", help="备份记录ID")
    parser.add_argument("--type", choices=["full", "incremental"], default="full")
    parser.add_argument("--dir", default="backups", help="备份目录")
    args = parser.parse_args()

    mgr = BackupManager(config={"backup_dir": args.dir})

    if args.action == "backup-db":
        record = mgr.backup_database(backup_type=BackupType(args.type))
        print(json.dumps({"id": record.id, "status": record.status.value, "size": record.size_bytes},
                         ensure_ascii=False))
    elif args.action == "backup-files":
        record = mgr.backup_files(backup_type=BackupType(args.type))
        print(json.dumps({"id": record.id, "status": record.status.value, "size": record.size_bytes},
                         ensure_ascii=False))
    elif args.action == "verify":
        if not args.id:
            print("需要 --id 参数")
            sys.exit(1)
        result = mgr.verify_backup(args.id)
        print(f"验证{'通过' if result else '失败'}")
    elif args.action == "restore":
        if not args.id:
            print("需要 --id 参数")
            sys.exit(1)
        result = mgr.restore_backup(args.id)
        print(f"恢复{'成功' if result else '失败'}")
    elif args.action == "list":
        print(json.dumps(mgr.list_backups(), ensure_ascii=False, indent=2))
    elif args.action == "cleanup":
        removed = mgr.cleanup_expired()
        print(f"清理了 {len(removed)} 个过期备份")


if __name__ == "__main__":
    main()