#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 迁移模块 - SQLite 到 PostgreSQL 数据迁移

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import sys
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """数据库配置"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL', 'sqlite:///acas_pro.db')
        self.is_postgres = self.database_url.startswith('postgresql')
        
        # 连接池配置
        self.pool_size = int(os.getenv('DB_POOL_SIZE', '10'))
        self.max_overflow = int(os.getenv('DB_MAX_OVERFLOW', '20'))
        self.pool_timeout = int(os.getenv('DB_POOL_TIMEOUT', '30'))
        self.pool_recycle = int(os.getenv('DB_POOL_RECYCLE', '3600'))


class DatabaseManager:
    """数据库管理器 - 支持 SQLite 和 PostgreSQL"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self._init_engine()
    
    def _init_engine(self):
        """初始化数据库引擎"""
        if self.config.is_postgres:
            # PostgreSQL 连接池配置
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                pool_pre_ping=True,  # 自动检测断开的连接
                echo=False
            )
        else:
            # SQLite 配置
            self.engine = create_engine(
                self.config.database_url,
                connect_args={'check_same_thread': False},
                echo=False
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"数据库引擎初始化: {'PostgreSQL' if self.config.is_postgres else 'SQLite'}")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def create_tables(self):
        """创建所有表"""
        from database import Base
        Base.metadata.create_all(bind=self.engine)
        logger.info("数据库表创建完成")
    
    def drop_tables(self):
        """删除所有表（危险操作）"""
        from database import Base
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("数据库表已删除")
    
    def check_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        stats = {
            "type": "PostgreSQL" if self.config.is_postgres else "SQLite",
            "url": self.config.database_url.replace(
                "://", "://***@").replace("//", "//***@") if "@" in self.config.database_url else self.config.database_url
        }
        
        if self.config.is_postgres:
            try:
                with self.engine.connect() as conn:
                    # 连接数
                    result = conn.execute(text("SELECT count(*) FROM pg_stat_activity"))
                    stats["connections"] = result.scalar()
                    
                    # 数据库大小
                    result = conn.execute(text(
                        "SELECT pg_size_pretty(pg_database_size(current_database()))"
                    ))
                    stats["size"] = result.scalar()
                    
                    # 表统计
                    result = conn.execute(text("""
                        SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                        FROM pg_stat_user_tables
                        ORDER BY n_tup_ins DESC
                    """))
                    stats["tables"] = [
                        {
                            "schema": row[0],
                            "table": row[1],
                            "inserts": row[2],
                            "updates": row[3],
                            "deletes": row[4]
                        }
                        for row in result
                    ]
            except Exception as e:
                logger.error(f"获取 PostgreSQL 统计失败: {e}")
        
        return stats


class MigrationManager:
    """迁移管理器 - SQLite 到 PostgreSQL"""
    
    # 表映射配置
    TABLES = [
        'users',
        'contents', 
        'accounts',
        'tasks',
        'video_projects',
        'analytics',
        'audit_logs'
    ]
    
    def __init__(self, sqlite_path: str = "acas_pro.db", pg_url: Optional[str] = None):
        self.sqlite_path = sqlite_path
        self.pg_url = pg_url or os.getenv('DATABASE_URL')
        
        if not self.pg_url or not self.pg_url.startswith('postgresql'):
            raise ValueError("必须提供 PostgreSQL 连接 URL")
        
        self.sqlite_engine = create_engine(f"sqlite:///{sqlite_path}")
        self.pg_engine = create_engine(
            self.pg_url,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10
        )
    
    def _get_sqlite_tables(self) -> List[str]:
        """获取 SQLite 中的所有表"""
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ))
            return [row[0] for row in result]
    
    def _get_table_schema(self, table_name: str) -> List[Dict]:
        """获取表结构"""
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = []
            for row in result:
                columns.append({
                    'cid': row[0],
                    'name': row[1],
                    'type': row[2],
                    'notnull': row[3],
                    'default': row[4],
                    'pk': row[5]
                })
            return columns
    
    def _migrate_table(self, table_name: str, batch_size: int = 1000) -> int:
        """迁移单个表"""
        logger.info(f"迁移表: {table_name}")
        
        # 获取 SQLite 数据
        with self.sqlite_engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = result.keys()
        
        if not rows:
            logger.info(f"  表 {table_name} 为空，跳过")
            return 0
        
        # 构建 INSERT 语句
        column_names = ', '.join(columns)
        placeholders = ', '.join([f':{col}' for col in columns])
        
        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        
        # 批量插入 PostgreSQL
        count = 0
        with self.pg_engine.connect() as conn:
            with conn.begin():
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    for row in batch:
                        row_dict = dict(zip(columns, row))
                        conn.execute(text(insert_sql), row_dict)
                        count += 1
                    
                    if (i // batch_size + 1) % 10 == 0:
                        logger.info(f"  已迁移 {count}/{len(rows)} 条记录")
        
        logger.info(f"  完成: {count} 条记录")
        return count
    
    def migrate(self, dry_run: bool = False) -> Dict[str, int]:
        """
        执行迁移
        
        Args:
            dry_run: 仅预览，不实际迁移
        
        Returns:
            各表迁移记录数
        """
        logger.info("=" * 60)
        logger.info("SQLite 到 PostgreSQL 迁移")
        logger.info("=" * 60)
        logger.info(f"源: {self.sqlite_path}")
        logger.info(f"目标: {self.pg_url.replace('://', '://***@')}")
        logger.info(f"模式: {'预览' if dry_run else '实际迁移'}")
        logger.info("=" * 60)
        
        # 获取源表
        tables = self._get_sqlite_tables()
        logger.info(f"发现 {len(tables)} 个表: {', '.join(tables)}")
        
        if dry_run:
            return {table: 0 for table in tables}
        
        # 执行迁移
        results = {}
        total = 0
        
        for table in tables:
            try:
                count = self._migrate_table(table)
                results[table] = count
                total += count
            except Exception as e:
                logger.error(f"迁移表 {table} 失败: {e}")
                results[table] = -1
        
        logger.info("=" * 60)
        logger.info(f"迁移完成: 总计 {total} 条记录")
        logger.info("=" * 60)
        
        return results
    
    def verify(self) -> bool:
        """验证迁移结果"""
        logger.info("验证迁移结果...")
        
        sqlite_tables = self._get_sqlite_tables()
        
        with self.pg_engine.connect() as conn:
            for table in sqlite_tables:
                # 检查表是否存在
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = :table
                    )
                """), {"table": table})
                
                if not result.scalar():
                    logger.error(f"表 {table} 在 PostgreSQL 中不存在")
                    return False
                
                # 检查记录数
                sqlite_count = self.sqlite_engine.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                
                pg_count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                
                if sqlite_count != pg_count:
                    logger.error(f"表 {table} 记录数不匹配: SQLite={sqlite_count}, PG={pg_count}")
                    return False
                
                logger.info(f"  {table}: {pg_count} 条记录 ✓")
        
        logger.info("验证通过！")
        return True


def init_postgres():
    """初始化 PostgreSQL 数据库"""
    config = DatabaseConfig()
    
    if not config.is_postgres:
        logger.warning("当前配置为 SQLite，跳过 PostgreSQL 初始化")
        return None
    
    manager = DatabaseManager(config)
    
    # 检查连接
    if not manager.check_connection():
        raise RuntimeError("无法连接到 PostgreSQL 数据库")
    
    # 创建表
    manager.create_tables()
    
    logger.info("PostgreSQL 初始化完成")
    return manager


def migrate_sqlite_to_postgres(sqlite_path: str = "acas_pro.db"):
    """执行 SQLite 到 PostgreSQL 的迁移"""
    pg_url = os.getenv('DATABASE_URL')
    
    if not pg_url:
        raise ValueError("请设置 DATABASE_URL 环境变量")
    
    if not os.path.exists(sqlite_path):
        logger.info(f"SQLite 文件 {sqlite_path} 不存在，跳过迁移")
        return
    
    migrator = MigrationManager(sqlite_path, pg_url)
    
    # 预览
    logger.info("预览迁移...")
    migrator.migrate(dry_run=True)
    
    # 确认
    confirm = input("确认执行迁移? [y/N]: ")
    if confirm.lower() != 'y':
        logger.info("迁移已取消")
        return
    
    # 执行迁移
    results = migrator.migrate()
    
    # 验证
    if migrator.verify():
        logger.info("迁移成功完成！")
    else:
        logger.error("迁移验证失败，请检查数据")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ACAS Pro 数据库管理工具")
    parser.add_argument("command", choices=["init", "migrate", "stats", "drop"])
    parser.add_argument("--sqlite-path", default="acas_pro.db", help="SQLite 文件路径")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    if args.command == "init":
        init_postgres()
    elif args.command == "migrate":
        migrate_sqlite_to_postgres(args.sqlite_path)
    elif args.command == "stats":
        config = DatabaseConfig()
        manager = DatabaseManager(config)
        import json
        print(json.dumps(manager.get_stats(), indent=2, default=str))
    elif args.command == "drop":
        confirm = input("警告: 这将删除所有数据！输入 'DROP' 确认: ")
        if confirm == "DROP":
            config = DatabaseConfig()
            manager = DatabaseManager(config)
            manager.drop_tables()
        else:
            print("已取消")
