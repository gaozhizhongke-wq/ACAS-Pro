# -*- coding: utf-8 -*-
"""
ACAS Pro - SQLAlchemy ORM Models
Database models for Alembic migrations and ORM operations
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Boolean, 
    DateTime, Text, ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship, Session
from sqlalchemy.sql import func

from acas_pro.core.config import config

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True)
    account = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    avatar = Column(String(500))
    role = Column(String(20), default='user')  # user, admin, super_admin
    status = Column(String(20), default='active')  # active, inactive, suspended
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)
    login_count = Column(Integer, default=0)
    
    # 关系
    accounts = relationship("SocialAccount", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user")


class SocialAccount(Base):
    """社交媒体账号表"""
    __tablename__ = 'social_accounts'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    platform = Column(String(50), nullable=False, index=True)  # douyin, xhs, kuaishou, bilibili
    platform_account_id = Column(String(100), nullable=False)
    username = Column(String(100))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    status = Column(String(20), default='active')  # active, expired, revoked
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="accounts")


class Product(Base):
    """商品表"""
    __tablename__ = 'products'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    price = Column(Float, default=0.0)
    original_price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    status = Column(String(20), default='draft')  # draft, active, inactive, sold_out
    platform = Column(String(50))  # taobao, jd, pdd, xhs
    platform_product_id = Column(String(100))
    shop_id = Column(String(36))
    images = Column(JSON, default=list)
    variants = Column(JSON, default=list)
    sales_count = Column(Integer, default=0)
    monthly_sales = Column(Integer, default=0)
    weekly_sales = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Order(Base):
    """订单表"""
    __tablename__ = 'orders'
    
    id = Column(String(36), primary_key=True)
    platform_order_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'))
    product_id = Column(String(36), ForeignKey('products.id'))
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(30), default='pending_payment')
    payment_status = Column(String(20), default='unpaid')
    shipping_address = Column(JSON)
    logistics = Column(JSON)
    buyer_id = Column(String(100))
    buyer_nickname = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    paid_at = Column(DateTime)
    shipped_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    user = relationship("User", back_populates="orders")


class ContentPost(Base):
    """内容发布表"""
    __tablename__ = 'content_posts'
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255))
    content = Column(Text)
    platform = Column(String(50), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey('social_accounts.id'))
    status = Column(String(20), default='draft')  # draft, scheduled, published, failed
    scheduled_at = Column(DateTime)
    published_at = Column(DateTime)
    media_urls = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    engagement_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TrendData(Base):
    """趋势数据表"""
    __tablename__ = 'trend_data'
    
    id = Column(String(36), primary_key=True)
    platform = Column(String(50), nullable=False, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    search_volume = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0)
    sentiment_score = Column(Float, default=0.0)
    related_keywords = Column(JSON, default=list)
    top_posts = Column(JSON, default=list)
    recorded_at = Column(DateTime, default=func.now())
    
    __table_args__ = (
        # 复合索引：平台+关键词+时间
        {'sqlite_autoincrement': True},
    )


class InventoryItem(Base):
    """库存表"""
    __tablename__ = 'inventory'
    
    id = Column(String(36), primary_key=True)
    product_id = Column(String(36), ForeignKey('products.id'), nullable=False)
    warehouse_id = Column(String(36))
    quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    reorder_point = Column(Integer, default=10)
    reorder_quantity = Column(Integer, default=100)
    last_restocked_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VideoProject(Base):
    """视频项目表"""
    __tablename__ = 'video_projects'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    width = Column(Integer, default=1080)
    height = Column(Integer, default=1920)
    fps = Column(Integer, default=30)
    duration = Column(Float, default=0.0)
    title = Column(String(255))
    description = Column(Text)
    script = Column(Text)
    clips = Column(JSON, default=list)
    background_music = Column(String(500))
    voice_over = Column(String(500))
    status = Column(String(20), default='draft')  # draft, rendering, completed, failed
    output_path = Column(String(500))
    target_platform = Column(String(50), default='douyin')
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VoiceTask(Base):
    """语音合成任务表"""
    __tablename__ = 'voice_tasks'
    
    id = Column(String(36), primary_key=True)
    text = Column(Text, nullable=False)
    voice_id = Column(String(50), nullable=False)
    language = Column(String(10))
    speed = Column(Float, default=1.0)
    pitch = Column(Float, default=1.0)
    volume = Column(Float, default=1.0)
    emotion = Column(String(20))
    output_path = Column(String(500))
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    duration = Column(Float)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)


class AuditLog(Base):
    """审计日志表"""
    __tablename__ = 'audit_logs'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36))
    action = Column(String(50), nullable=False)  # login, logout, create, update, delete
    resource_type = Column(String(50))  # user, product, order, content
    resource_id = Column(String(36))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    status = Column(String(20), default='success')  # success, failure
    created_at = Column(DateTime, default=func.now())


# 数据库连接工厂
def get_engine():
    """获取 SQLAlchemy 引擎"""
    db_config = config.database
    if db_config.type == 'postgresql':
        url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
    else:
        url = f"sqlite:///{db_config.path}"
    return create_engine(url, echo=db_config.echo, pool_pre_ping=True)


def init_database():
    """初始化数据库（创建所有表）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    """获取数据库会话"""
    engine = get_engine()
    return Session(engine)
