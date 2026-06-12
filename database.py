#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 数据持久化层
SQLite + SQLAlchemy，零配置，开箱即用
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()

# ========== 数据模型 ==========

class Account(Base):
    """社媒账号"""
    __tablename__ = 'accounts'
    
    id = Column(String(32), primary_key=True)
    platform = Column(String(50), nullable=False)  # weibo, douyin, etc.
    username = Column(String(100), nullable=False)
    status = Column(String(20), default='active')  # active, suspended, inactive
    followers = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    config = Column(Text, default='{}')  # JSON 配置

class Content(Base):
    """内容创作"""
    __tablename__ = 'contents'
    
    id = Column(String(32), primary_key=True)
    title = Column(String(200))
    content = Column(Text)
    platform = Column(String(50))
    content_type = Column(String(20))  # article, video, image
    status = Column(String(20), default='draft')  # draft, published, scheduled
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    meta_data = Column(Text, default='{}')  # JSON 元数据

class Customer(Base):
    """客户数据"""
    __tablename__ = 'customers'
    
    id = Column(String(32), primary_key=True)
    name = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    source = Column(String(50))  # 获客渠道
    status = Column(String(20), default='new')  # new, contacted, converted, lost
    tags = Column(Text, default='[]')  # JSON 标签
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Campaign(Base):
    """营销活动"""
    __tablename__ = 'campaigns'
    
    id = Column(String(32), primary_key=True)
    name = Column(String(200), nullable=False)
    campaign_type = Column(String(50))  # festival, flash_sale, etc.
    status = Column(String(20), default='draft')
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    budget = Column(Float, default=0)
    spent = Column(Float, default=0)
    target_audience = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Settlement(Base):
    """结算记录"""
    __tablename__ = 'settlements'
    
    id = Column(String(32), primary_key=True)
    settlement_type = Column(String(50))  # revenue, expense, commission
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default='CNY')
    status = Column(String(20), default='pending')  # pending, completed, cancelled
    party_name = Column(String(100))
    party_id = Column(String(32))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

class SystemLog(Base):
    """系统日志"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(String(20), default='INFO')  # DEBUG, INFO, WARNING, ERROR
    module = Column(String(50))
    message = Column(Text, nullable=False)
    details = Column(Text)  # JSON 详细信息
    created_at = Column(DateTime, default=datetime.utcnow)

# ========== 数据库管理 ==========

class Database:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "acas_pro.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        return self.Session()
    
    # ===== 账号管理 =====
    def create_account(self, account_id: str, platform: str, username: str, **kwargs) -> Account:
        with self.get_session() as session:
            account = Account(
                id=account_id,
                platform=platform,
                username=username,
                **kwargs
            )
            session.add(account)
            session.commit()
            return account
    
    def get_accounts(self, platform: str = None, status: str = None) -> List[Account]:
        with self.get_session() as session:
            query = session.query(Account)
            if platform:
                query = query.filter(Account.platform == platform)
            if status:
                query = query.filter(Account.status == status)
            return query.all()
    
    # ===== 客户管理 =====
    def create_customer(self, customer_id: str, name: str, **kwargs) -> Customer:
        with self.get_session() as session:
            customer = Customer(id=customer_id, name=name, **kwargs)
            session.add(customer)
            session.commit()
            return customer
    
    def get_customers(self, status: str = None, source: str = None) -> List[Customer]:
        with self.get_session() as session:
            query = session.query(Customer)
            if status:
                query = query.filter(Customer.status == status)
            if source:
                query = query.filter(Customer.source == source)
            return query.all()
    
    # ===== 内容管理 =====
    def create_content(self, content_id: str, title: str, **kwargs) -> Content:
        with self.get_session() as session:
            content = Content(id=content_id, title=title, **kwargs)
            session.add(content)
            session.commit()
            return content
    
    def get_contents(self, status: str = None, platform: str = None) -> List[Content]:
        with self.get_session() as session:
            query = session.query(Content)
            if status:
                query = query.filter(Content.status == status)
            if platform:
                query = query.filter(Content.platform == platform)
            return query.order_by(Content.created_at.desc()).all()
    
    # ===== 活动管理 =====
    def create_campaign(self, campaign_id: str, name: str, **kwargs) -> Campaign:
        with self.get_session() as session:
            campaign = Campaign(id=campaign_id, name=name, **kwargs)
            session.add(campaign)
            session.commit()
            return campaign
    
    def get_campaigns(self, status: str = None) -> List[Campaign]:
        with self.get_session() as session:
            query = session.query(Campaign)
            if status:
                query = query.filter(Campaign.status == status)
            return query.order_by(Campaign.created_at.desc()).all()
    
    # ===== 结算管理 =====
    def create_settlement(self, settlement_id: str, settlement_type: str, amount: float, **kwargs) -> Settlement:
        with self.get_session() as session:
            settlement = Settlement(
                id=settlement_id,
                settlement_type=settlement_type,
                amount=amount,
                **kwargs
            )
            session.add(settlement)
            session.commit()
            return settlement
    
    def get_settlements(self, status: str = None, settlement_type: str = None) -> List[Settlement]:
        with self.get_session() as session:
            query = session.query(Settlement)
            if status:
                query = query.filter(Settlement.status == status)
            if settlement_type:
                query = query.filter(Settlement.settlement_type == settlement_type)
            return query.order_by(Settlement.created_at.desc()).all()
    
    # ===== 日志管理 =====
    def log(self, level: str, module: str, message: str, details: dict = None):
        with self.get_session() as session:
            log_entry = SystemLog(
                level=level,
                module=module,
                message=message,
                details=json.dumps(details) if details else None
            )
            session.add(log_entry)
            session.commit()
    
    def get_logs(self, level: str = None, module: str = None, limit: int = 100) -> List[SystemLog]:
        with self.get_session() as session:
            query = session.query(SystemLog)
            if level:
                query = query.filter(SystemLog.level == level)
            if module:
                query = query.filter(SystemLog.module == module)
            return query.order_by(SystemLog.created_at.desc()).limit(limit).all()
    
    # ===== 统计 =====
    def get_dashboard_stats(self) -> Dict[str, Any]:
        with self.get_session() as session:
            return {
                "total_accounts": session.query(Account).count(),
                "active_accounts": session.query(Account).filter(Account.status == 'active').count(),
                "total_customers": session.query(Customer).count(),
                "new_customers_today": session.query(Customer).filter(
                    Customer.created_at >= datetime.now().replace(hour=0, minute=0, second=0)
                ).count(),
                "total_campaigns": session.query(Campaign).count(),
                "active_campaigns": session.query(Campaign).filter(Campaign.status == 'active').count(),
                "pending_settlements": session.query(Settlement).filter(Settlement.status == 'pending').count(),
                "total_revenue": session.query(Settlement).filter(
                    Settlement.settlement_type == 'revenue',
                    Settlement.status == 'completed'
                ).with_entities(Settlement.amount).all()
            }


# 全局数据库实例
_db: Optional[Database] = None

def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


if __name__ == "__main__":
    # 测试数据库
    db = get_db()
    
    # 添加测试数据
    import uuid
    
    # 测试账号
    db.create_account(
        account_id=str(uuid.uuid4())[:8],
        platform="weibo",
        username="test_account",
        followers=1000
    )
    
    # 测试客户
    db.create_customer(
        customer_id=str(uuid.uuid4())[:8],
        name="测试客户",
        phone="13800138000",
        source="weibo"
    )
    
    # 测试日志
    db.log("INFO", "test", "数据库初始化完成")
    
    # 获取统计
    stats = db.get_dashboard_stats()
    print("Dashboard Stats:", stats)
    print("\n✅ 数据库测试通过")
