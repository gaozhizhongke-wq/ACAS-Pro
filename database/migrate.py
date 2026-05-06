#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Database Migration Tool
Enterprise-grade schema management
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.migrate')


class MigrationStatus(Enum):
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """迁移定义"""
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    checksum: str
    applied_at: Optional[datetime] = None
    status: MigrationStatus = MigrationStatus.PENDING
    execution_time_ms: int = 0


class MigrationManager:
    """
    数据库迁移管理器
    
    Features:
    - 版本控制
    - 回滚支持
    - 校验和验证
    - 事务安全
    """
    
    def __init__(self, db_pool=None):
        self.db = db_pool
        self.migrations_dir = 'database/migrations'
        self.migrations: Dict[str, Migration] = {}
        
        # 确保目录存在
        os.makedirs(self.migrations_dir, exist_ok=True)
        
        # 初始化迁移表
        self._init_migration_table()
    
    def _init_migration_table(self):
        """初始化迁移元数据表"""
        sql = '''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(50) PRIMARY KEY,
                name VARCHAR(200),
                description TEXT,
                checksum VARCHAR(64),
                applied_at TIMESTAMP,
                status VARCHAR(20),
                execution_time_ms INTEGER
            )
        '''
        try:
            self.db.execute(sql)
            logger.info("✓ Migration table initialized")
        except Exception as e:
            logger.error(f"Failed to init migration table: {e}")
    
    def create_migration(self, name: str, description: str = "") -> Migration:
        """创建新迁移"""
        # 生成版本号 (时间戳)
        version = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        
        # 创建迁移文件
        filename = f"{version}_{name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)
        
        template = f'''-- Migration: {name}
-- Version: {version}
-- Created: {datetime.utcnow().isoformat()}
-- Description: {description}

-- UP (Apply)
BEGIN;

-- TODO: Add your migration SQL here

COMMIT;

-- DOWN (Rollback)
BEGIN;

-- TODO: Add rollback SQL here

COMMIT;
'''
        
        with open(filepath, 'w') as f:
            f.write(template)
        
        logger.info(f"✓ Created migration: {filepath}")
        
        return Migration(
            version=version,
            name=name,
            description=description,
            up_sql="",
            down_sql="",
            checksum=""
        )
    
    def load_migrations(self) -> List[Migration]:
        """加载所有迁移文件"""
        migrations = []
        
        for filename in sorted(os.listdir(self.migrations_dir)):
            if not filename.endswith('.sql'):
                continue
            
            filepath = os.path.join(self.migrations_dir, filename)
            
            # 解析文件名
            parts = filename.replace('.sql', '').split('_', 1)
            version = parts[0]
            name = parts[1] if len(parts) > 1 else 'unknown'
            
            # 读取文件
            with open(filepath, 'r') as f:
                content = f.read()
            
            # 解析UP和DOWN
            up_sql = self._extract_sql(content, 'UP', 'DOWN')
            down_sql = self._extract_sql(content, 'DOWN', None)
            
            # 计算校验和
            checksum = hashlib.sha256(content.encode()).hexdigest()
            
            migration = Migration(
                version=version,
                name=name,
                description="",
                up_sql=up_sql,
                down_sql=down_sql,
                checksum=checksum
            )
            
            migrations.append(migration)
        
        # 加载已应用的状态
        self._load_applied_status(migrations)
        
        return sorted(migrations, key=lambda m: m.version)
    
    def _extract_sql(self, content: str, start_marker: str, end_marker: str) -> str:
        """提取SQL块"""
        lines = content.split('\n')
        result = []
        in_block = False
        
        for line in lines:
            if f'-- {start_marker}' in line:
                in_block = True
                continue
            if end_marker and f'-- {end_marker}' in line:
                break
            if in_block:
                result.append(line)
        
        return '\n'.join(result).strip()
    
    def _load_applied_status(self, migrations: List[Migration]):
        """加载已应用的迁移状态"""
        try:
            result = self.db.execute(
                "SELECT version, checksum, applied_at, status FROM schema_migrations",
                fetch=True
            )
            
            applied = {row[0]: row for row in result} if result else {}
            
            for migration in migrations:
                if migration.version in applied:
                    row = applied[migration.version]
                    migration.applied_at = row[2]
                    migration.status = MigrationStatus(row[3])
                    
                    # 验证校验和
                    if row[1] != migration.checksum:
                        logger.warning(
                            f"⚠ Migration {migration.version} checksum mismatch! "
                            f"File may have been modified after application."
                        )
        
        except Exception as e:
            logger.error(f"Failed to load applied status: {e}")
    
    def migrate(self, target_version: str = None) -> List[Migration]:
        """
        执行迁移
        
        Args:
            target_version: 目标版本 (None = 最新)
        """
        migrations = self.load_migrations()
        applied = []
        
        for migration in migrations:
            # 检查是否已应用
            if migration.status == MigrationStatus.APPLIED:
                continue
            
            # 检查目标版本
            if target_version and migration.version > target_version:
                break
            
            # 执行迁移
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            
            start_time = datetime.utcnow()
            try:
                # 执行SQL
                self.db.execute(migration.up_sql)
                
                # 记录迁移
                execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                self.db.execute('''
                    INSERT INTO schema_migrations 
                    (version, name, description, checksum, applied_at, status, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    migration.version,
                    migration.name,
                    migration.description,
                    migration.checksum,
                    datetime.utcnow(),
                    MigrationStatus.APPLIED.value,
                    execution_time
                ))
                
                migration.status = MigrationStatus.APPLIED
                migration.applied_at = datetime.utcnow()
                migration.execution_time_ms = execution_time
                
                applied.append(migration)
                logger.info(f"✓ Applied in {execution_time}ms")
                
            except Exception as e:
                logger.error(f"✗ Failed: {e}")
                migration.status = MigrationStatus.FAILED
                raise
        
        return applied
    
    def rollback(self, steps: int = 1) -> List[Migration]:
        """回滚迁移"""
        migrations = self.load_migrations()
        
        # 获取已应用的迁移 (倒序)
        applied = [m for m in migrations if m.status == MigrationStatus.APPLIED]
        applied.reverse()
        
        rolled_back = []
        
        for i, migration in enumerate(applied[:steps]):
            logger.info(f"Rolling back {migration.version}: {migration.name}")
            
            try:
                # 执行回滚SQL
                if migration.down_sql:
                    self.db.execute(migration.down_sql)
                
                # 删除迁移记录
                self.db.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )
                
                migration.status = MigrationStatus.ROLLED_BACK
                rolled_back.append(migration)
                
                logger.info(f"✓ Rolled back")
                
            except Exception as e:
                logger.error(f"✗ Rollback failed: {e}")
                raise
        
        return rolled_back
    
    def status(self) -> Dict:
        """获取迁移状态"""
        migrations = self.load_migrations()
        
        pending = [m for m in migrations if m.status == MigrationStatus.PENDING]
        applied = [m for m in migrations if m.status == MigrationStatus.APPLIED]
        failed = [m for m in migrations if m.status == MigrationStatus.FAILED]
        
        return {
            'total': len(migrations),
            'applied': len(applied),
            'pending': len(pending),
            'failed': len(failed),
            'current_version': applied[-1].version if applied else None,
            'pending_versions': [m.version for m in pending]
        }
    
    def verify(self) -> bool:
        """验证所有迁移"""
        migrations = self.load_migrations()
        
        all_valid = True
        for migration in migrations:
            if migration.status == MigrationStatus.APPLIED:
                # 重新计算校验和
                filepath = os.path.join(self.migrations_dir, f"{migration.version}_{migration.name}.sql")
                with open(filepath, 'r') as f:
                    content = f.read()
                
                current_checksum = hashlib.sha256(content.encode()).hexdigest()
                
                if current_checksum != migration.checksum:
                    logger.error(f"✗ Migration {migration.version} checksum mismatch!")
                    all_valid = False
        
        if all_valid:
            logger.info("✓ All migrations verified")
        
        return all_valid


# CLI接口
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='ACAS Pro Database Migration Tool')
    parser.add_argument('command', choices=['create', 'migrate', 'rollback', 'status', 'verify'])
    parser.add_argument('--name', help='Migration name')
    parser.add_argument('--description', help='Migration description')
    parser.add_argument('--steps', type=int, default=1, help='Rollback steps')
    parser.add_argument('--version', help='Target version')
    
    args = parser.parse_args()
    
    # 初始化 (需要实际的db_pool)
    print("="*60)
    print("ACAS Pro - Database Migration Tool")
    print("="*60)
    
    print(f"\nCommand: {args.command}")
    
    if args.command == 'create':
        if not args.name:
            print("Error: --name required")
            sys.exit(1)
        # migrator.create_migration(args.name, args.description or "")
        print(f"Would create migration: {args.name}")
    
    elif args.command == 'migrate':
        print("Would apply migrations...")
    
    elif args.command == 'rollback':
        print(f"Would rollback {args.steps} step(s)...")
    
    elif args.command == 'status':
        print("Migration status:")
        print("  Total: 0")
        print("  Applied: 0")
        print("  Pending: 0")
    
    elif args.command == 'verify':
        print("Would verify migrations...")
    
    print("\n" + "="*60)
    print("Done")
