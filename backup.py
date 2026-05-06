#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 数据备份系统
支持：自动备份、压缩、清理旧备份
"""

import os
import sys
import gzip
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from logger import app_logger, log_execution

# 备份配置
BACKUP_DIR = Path("backups")
BACKUP_DIR.mkdir(exist_ok=True)

DB_FILE = Path("acas_pro.db")
MAX_BACKUPS = 10  # 保留最近10个备份


class BackupManager:
    """备份管理器"""
    
    def __init__(self, db_path: str = "acas_pro.db", backup_dir: str = "backups"):
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    @log_execution(app_logger)
    def create_backup(self, name: Optional[str] = None) -> Path:
        """创建数据库备份"""
        if not self.db_path.exists():
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = name or f"acas_pro_{timestamp}"
        backup_path = self.backup_dir / f"{backup_name}.db.gz"
        
        # 压缩备份
        with sqlite3.connect(self.db_path) as src:
            # 验证数据库完整性
            result = src.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"数据库完整性检查失败: {result[0]}")
            
            # 创建备份
            with gzip.open(backup_path, 'wb') as dst:
                src.backup(dst)
        
        app_logger.info(f"备份创建成功: {backup_path} ({backup_path.stat().st_size / 1024:.1f} KB)")
        
        # 清理旧备份
        self._cleanup_old_backups()
        
        return backup_path
    
    @log_execution(app_logger)
    def restore_backup(self, backup_path: Path, target_path: Optional[Path] = None) -> Path:
        """从备份恢复数据库"""
        if not backup_path.exists():
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")
        
        target = target_path or self.db_path
        
        # 先备份当前数据库
        if target.exists():
            backup_current = self.backup_dir / f"acas_pro_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(target, backup_current)
            app_logger.info(f"当前数据库已备份到: {backup_current}")
        
        # 解压恢复
        with gzip.open(backup_path, 'rb') as src:
            with open(target, 'wb') as dst:
                shutil.copyfileobj(src, dst)
        
        # 验证恢复的数据库
        with sqlite3.connect(target) as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result[0] != "ok":
                raise RuntimeError(f"恢复后的数据库完整性检查失败: {result[0]}")
        
        app_logger.info(f"数据库恢复成功: {backup_path} -> {target}")
        return target
    
    def list_backups(self) -> List[dict]:
        """列出所有备份"""
        backups = []
        for backup_file in sorted(self.backup_dir.glob("*.db.gz"), reverse=True):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.name,
                'path': str(backup_file),
                'size': stat.st_size,
                'size_human': f"{stat.st_size / 1024:.1f} KB",
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        return backups
    
    def _cleanup_old_backups(self):
        """清理旧备份，只保留最近的 MAX_BACKUPS 个"""
        backups = sorted(self.backup_dir.glob("*.db.gz"), 
                        key=lambda x: x.stat().st_mtime, 
                        reverse=True)
        
        for old_backup in backups[MAX_BACKUPS:]:
            old_backup.unlink()
            app_logger.info(f"清理旧备份: {old_backup.name}")
    
    @log_execution(app_logger)
    def export_to_csv(self, export_dir: str = "exports") -> List[Path]:
        """导出所有表为 CSV"""
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)
        
        exported = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        with sqlite3.connect(self.db_path) as conn:
            # 获取所有表
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            
            for (table_name,) in tables:
                if table_name.startswith('sqlite_'):
                    continue
                
                csv_path = export_path / f"{table_name}_{timestamp}.csv"
                
                # 导出 CSV
                import csv
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    cursor = conn.execute(f"SELECT * FROM {table_name}")
                    headers = [desc[0] for desc in cursor.description]
                    
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(cursor.fetchall())
                
                exported.append(csv_path)
                app_logger.info(f"导出表 {table_name}: {csv_path}")
        
        return exported


# 定时备份任务
def scheduled_backup():
    """定时备份入口"""
    manager = BackupManager()
    try:
        backup_path = manager.create_backup()
        print(f"定时备份完成: {backup_path}")
    except Exception as e:
        app_logger.error(f"定时备份失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ACAS Pro 备份工具')
    parser.add_argument('action', choices=['create', 'list', 'restore', 'export'], 
                       help='操作类型')
    parser.add_argument('--file', help='备份文件路径 (用于 restore)')
    parser.add_argument('--name', help='备份名称 (可选)')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.action == 'create':
        path = manager.create_backup(args.name)
        print(f"备份创建成功: {path}")
    
    elif args.action == 'list':
        backups = manager.list_backups()
        if not backups:
            print("暂无备份")
        else:
            print(f"{'名称':<40} {'大小':<12} {'创建时间'}")
            print("-" * 80)
            for b in backups:
                print(f"{b['name']:<40} {b['size_human']:<12} {b['created']}")
    
    elif args.action == 'restore':
        if not args.file:
            print("错误: --file 参数必需")
            sys.exit(1)
        manager.restore_backup(Path(args.file))
        print("恢复完成")
    
    elif args.action == 'export':
        paths = manager.export_to_csv()
        print(f"导出完成: {len(paths)} 个文件")
        for p in paths:
            print(f"  - {p}")
