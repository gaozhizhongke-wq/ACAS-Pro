#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份与恢复模块

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import gzip
import shutil
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class BackupManager:
    """备份管理器"""
    
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        self.db_url = os.getenv('DATABASE_URL', 'sqlite:///acas_pro.db')
        self.is_postgres = self.db_url.startswith('postgresql')
    
    def _generate_backup_name(self, suffix: str = "") -> str:
        """生成备份文件名"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        db_type = "pg" if self.is_postgres else "sqlite"
        suffix_str = f"_{suffix}" if suffix else ""
        return f"acas_{db_type}_backup_{timestamp}{suffix_str}"
    
    def backup_sqlite(self) -> Path:
        """备份 SQLite 数据库"""
        db_path = self.db_url.replace('sqlite:///', '')
        db_file = Path(db_path)
        
        if not db_file.exists():
            raise FileNotFoundError(f"数据库文件不存在: {db_path}")
        
        backup_name = self._generate_backup_name()
        backup_path = self.backup_dir / f"{backup_name}.db.gz"
        
        # 压缩备份
        with open(db_file, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        logger.info(f"SQLite 备份完成: {backup_path}")
        return backup_path
    
    def backup_postgres(self) -> Path:
        """备份 PostgreSQL 数据库"""
        backup_name = self._generate_backup_name()
        backup_path = self.backup_dir / f"{backup_name}.sql.gz"
        
        # 使用 pg_dump
        cmd = [
            'pg_dump',
            '--dbname', self.db_url,
            '--format', 'plain',
            '--verbose'
        ]
        
        with gzip.open(backup_path, 'wb') as f_out:
            result = subprocess.run(cmd, stdout=f_out, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump 失败: {result.stderr.decode()}")
        
        logger.info(f"PostgreSQL 备份完成: {backup_path}")
        return backup_path
    
    def backup(self) -> Path:
        """执行备份"""
        if self.is_postgres:
            return self.backup_postgres()
        else:
            return self.backup_sqlite()
    
    def restore_sqlite(self, backup_path: Path, target_path: Optional[str] = None) -> Path:
        """恢复 SQLite 数据库"""
        if target_path is None:
            target_path = self.db_url.replace('sqlite:///', '')
        
        target = Path(target_path)
        
        # 备份当前数据库
        if target.exists():
            backup_current = target.with_suffix(f".db.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            shutil.copy2(target, backup_current)
            logger.info(f"当前数据库已备份到: {backup_current}")
        
        # 解压恢复
        with gzip.open(backup_path, 'rb') as f_in:
            with open(target, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        logger.info(f"SQLite 恢复完成: {target}")
        return target
    
    def restore_postgres(self, backup_path: Path) -> bool:
        """恢复 PostgreSQL 数据库"""
        # 使用 psql 恢复
        cmd = ['psql', self.db_url]
        
        with gzip.open(backup_path, 'rb') as f_in:
            result = subprocess.run(cmd, stdin=f_in, stderr=subprocess.PIPE)
        
        if result.returncode != 0:
            raise RuntimeError(f"psql 恢复失败: {result.stderr.decode()}")
        
        logger.info("PostgreSQL 恢复完成")
        return True
    
    def restore(self, backup_path: Path) -> bool:
        """执行恢复"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        # 确认
        logger.warning(f"即将从 {backup_path} 恢复数据库")
        logger.warning("当前数据将被覆盖！")
        
        if self.is_postgres:
            return self.restore_postgres(backup_path)
        else:
            self.restore_sqlite(backup_path)
            return True
    
    def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("*.gz"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                "file": backup_file.name,
                "path": str(backup_file),
                "size": self._format_size(stat.st_size),
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return backups
    
    def cleanup_old_backups(self, keep_days: int = 7):
        """清理旧备份"""
        cutoff = datetime.now() - timedelta(days=keep_days)
        cleaned = 0
        
        for backup_file in self.backup_dir.glob("*.gz"):
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            if mtime < cutoff:
                backup_file.unlink()
                cleaned += 1
                logger.info(f"删除旧备份: {backup_file.name}")
        
        logger.info(f"清理完成: 删除了 {cleaned} 个旧备份")
        return cleaned
    
    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class AutoBackup:
    """自动备份任务"""
    
    def __init__(self, backup_manager: BackupManager):
        self.manager = backup_manager
    
    def setup_windows_task(self, hour: int = 3, minute: int = 0) -> bool:
        """设置 Windows 计划任务"""
        try:
            script_path = Path(__file__).parent / "backup.py"
            
            ps_script = f'''
$action = New-ScheduledTaskAction -Execute "python" -Argument "{script_path} backup"
$trigger = New-ScheduledTaskTrigger -Daily -At "{hour:D2}:{minute:D2}"
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "ACAS-Daily-Backup" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force
'''
            subprocess.run(["powershell", "-Command", ps_script], check=True)
            logger.info(f"Windows 自动备份任务已创建: 每天 {hour:02d}:{minute:02d}")
            return True
        except Exception as e:
            logger.error(f"创建 Windows 任务失败: {e}")
            return False
    
    def setup_linux_cron(self, hour: int = 3, minute: int = 0) -> bool:
        """设置 Linux Cron 任务"""
        try:
            script_path = Path(__file__).parent / "backup.py"
            cron_line = f"{minute} {hour} * * * cd {Path(__file__).parent} && python {script_path} backup >> /var/log/acas_backup.log 2>&1\n"
            
            subprocess.run(
                f"(crontab -l 2>/dev/null; echo '{cron_line}') | crontab -",
                shell=True, check=True
            )
            logger.info(f"Linux 自动备份任务已创建: 每天 {hour:02d}:{minute:02d}")
            return True
        except Exception as e:
            logger.error(f"创建 Linux Cron 失败: {e}")
            return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ACAS Pro 数据库备份工具")
    parser.add_argument("command", choices=["backup", "restore", "list", "cleanup", "auto"])
    parser.add_argument("--file", help="备份文件路径（用于恢复）")
    parser.add_argument("--keep-days", type=int, default=7, help="保留天数")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    manager = BackupManager()
    
    if args.command == "backup":
        backup_path = manager.backup()
        print(f"备份完成: {backup_path}")
    
    elif args.command == "restore":
        if not args.file:
            print("错误: 恢复操作需要 --file 参数")
            exit(1)
        manager.restore(Path(args.file))
    
    elif args.command == "list":
        backups = manager.list_backups()
        if backups:
            print(f"{'文件名':<50} {'大小':<12} {'创建时间'}")
            print("-" * 90)
            for b in backups:
                print(f"{b['file']:<50} {b['size']:<12} {b['created']}")
        else:
            print("暂无备份")
    
    elif args.command == "cleanup":
        manager.cleanup_old_backups(args.keep_days)
    
    elif args.command == "auto":
        # 执行备份并清理旧备份
        manager.backup()
        manager.cleanup_old_backups(args.keep_days)
