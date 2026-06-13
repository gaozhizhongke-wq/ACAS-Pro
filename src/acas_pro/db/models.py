# -*- coding: utf-8 -*-
"""
ACAS Pro - SQLAlchemy ORM Models
Database models for Alembic migrations and ORM operations
"""

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship, Session, validates
from sqlalchemy.sql import func

from acas_pro.core.config import config

Base: type = declarative_base()  # type: ignore[valid-type]


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    account = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    @validates("password_hash")
    def _validate_password_hash(self, key: str, value: str) -> str:
        """Ensure stored password_hash uses PBKDF2 format (not plaintext)."""
        if not value.startswith("pbkdf2:sha256:"):
            raise ValueError(
                f"password_hash must use PBKDF2 format, got: {value[:20]}..."
            )
        return value
    nickname = Column(String(100))
    email = Column(String(255), index=True)
    phone = Column(String(20), index=True)
    avatar = Column(String(500))
    role = Column(String(20), default="user", index=True)  # user, admin, super_admin
    status = Column(
        String(20), default="active", index=True
    )  # active, inactive, suspended
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime)
    login_count = Column(Integer, default=0)

    # 关系
    accounts = relationship(
        "SocialAccount", back_populates="user", cascade="all, delete-orphan"
    )
    orders = relationship("Order", back_populates="user")


class SocialAccount(Base):
    """社交媒体账号表"""

    __tablename__ = "social_accounts"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(
        String(50), nullable=False, index=True
    )  # douyin, xhs, kuaishou, bilibili
    platform_account_id = Column(String(100), nullable=False, index=True)
    username = Column(String(100))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    status = Column(
        String(20), default="active", index=True
    )  # active, expired, revoked
    follower_count = Column(Integer, default=0)
    following_count = Column(Integer, default=0)
    post_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="accounts")


class Product(Base):
    """商品表"""

    __tablename__ = "products"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    price = Column(Float, default=0.0)
    original_price = Column(Float, default=0.0)
    stock = Column(Integer, default=0)
    status = Column(
        String(20), default="draft", index=True
    )  # draft, active, inactive, sold_out
    platform = Column(String(50), index=True)  # taobao, jd, pdd, xhs
    platform_product_id = Column(String(100))
    shop_id = Column(String(36), index=True)
    images = Column(JSON, default=list)
    variants = Column(JSON, default=list)
    sales_count = Column(Integer, default=0, index=True)
    monthly_sales = Column(Integer, default=0)
    weekly_sales = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Order(Base):
    """订单表"""

    __tablename__ = "orders"

    id = Column(String(36), primary_key=True)
    platform_order_id = Column(String(100), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), index=True)
    product_id = Column(String(36), ForeignKey("products.id"), index=True)
    items = Column(JSON, default=list)
    subtotal = Column(Float, default=0.0)
    shipping_fee = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(30), default="pending_payment", index=True)
    payment_status = Column(String(20), default="unpaid", index=True)
    shipping_address = Column(JSON)
    logistics = Column(JSON)
    buyer_id = Column(String(100))
    buyer_nickname = Column(String(100))
    created_at = Column(DateTime, default=func.now(), index=True)
    paid_at = Column(DateTime)
    shipped_at = Column(DateTime)
    completed_at = Column(DateTime)

    user = relationship("User", back_populates="orders")


class ContentPost(Base):
    """内容发布表"""

    __tablename__ = "content_posts"

    id = Column(String(36), primary_key=True)
    title = Column(String(255))
    content = Column(Text)
    platform = Column(String(50), nullable=False, index=True)
    account_id = Column(String(36), ForeignKey("social_accounts.id"), index=True)
    status = Column(
        String(20), default="draft", index=True
    )  # draft, scheduled, published, failed
    scheduled_at = Column(DateTime, index=True)
    published_at = Column(DateTime, index=True)
    media_urls = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    engagement_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TrendData(Base):
    """趋势数据表"""

    __tablename__ = "trend_data"

    id = Column(String(36), primary_key=True)
    platform = Column(String(50), nullable=False, index=True)
    keyword = Column(String(255), nullable=False, index=True)
    search_volume = Column(Integer, default=0, index=True)
    growth_rate = Column(Float, default=0.0, index=True)
    sentiment_score = Column(Float, default=0.0)
    related_keywords = Column(JSON, default=list)
    top_posts = Column(JSON, default=list)
    recorded_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        # 复合索引：平台+关键词+时间
        Index("idx_platform_keyword_recorded", "platform", "keyword", "recorded_at"),
    )


class InventoryItem(Base):
    """库存表"""

    __tablename__ = "inventory"

    id = Column(String(36), primary_key=True)
    product_id = Column(
        String(36), ForeignKey("products.id"), nullable=False, index=True
    )
    warehouse_id = Column(String(36), index=True)
    quantity = Column(Integer, default=0, index=True)
    reserved_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    reorder_point = Column(Integer, default=10)
    reorder_quantity = Column(Integer, default=100)
    last_restocked_at = Column(DateTime)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VideoProject(Base):
    """视频项目表"""

    __tablename__ = "video_projects"

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
    status = Column(
        String(20), default="draft", index=True
    )  # draft, rendering, completed, failed
    output_path = Column(String(500))
    target_platform = Column(String(50), default="douyin", index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VoiceTask(Base):
    """语音合成任务表"""

    __tablename__ = "voice_tasks"

    id = Column(String(36), primary_key=True)
    text = Column(Text, nullable=False)
    voice_id = Column(String(50), nullable=False, index=True)
    language = Column(String(10))
    speed = Column(Float, default=1.0)
    pitch = Column(Float, default=1.0)
    volume = Column(Float, default=1.0)
    emotion = Column(String(20))
    output_path = Column(String(500))
    status = Column(
        String(20), default="pending", index=True
    )  # pending, processing, completed, failed
    duration = Column(Float)
    created_at = Column(DateTime, default=func.now(), index=True)
    completed_at = Column(DateTime, index=True)


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True)
    action = Column(
        String(50), nullable=False, index=True
    )  # login, logout, create, update, delete
    resource_type = Column(String(50), index=True)  # user, product, order, content
    resource_id = Column(String(36), index=True)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    status = Column(String(20), default="success", index=True)  # success, failure
    created_at = Column(DateTime, default=func.now(), index=True)

    __table_args__ = (
        # 复合索引：用户+操作+时间
        Index("idx_user_action_time", "user_id", "action", "created_at"),
        # 复合索引：资源类型+资源ID+时间
        Index("idx_resource_time", "resource_type", "resource_id", "created_at"),
    )


# 数据库连接工厂
def get_engine() -> None:
    """获取 SQLAlchemy 引擎"""
    db_config = config.database
    if db_config.type == "postgresql":
        url = f"postgresql://{db_config.user}:{db_config.password}@{db_config.host}:{db_config.port}/{db_config.database}"
    else:
        url = f"sqlite:///{db_config.path}"
    return create_engine(url, echo=db_config.echo, pool_pre_ping=True)


def init_database() -> None:
    """初始化数据库（创建所有表）"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    """获取数据库会话"""
    engine = get_engine()
    return Session(engine)
