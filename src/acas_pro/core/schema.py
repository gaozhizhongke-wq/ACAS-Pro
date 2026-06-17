#!/usr/bin/env python3
"""
ACAS Pro — Unified Schema Registry

ALL table definitions live here.  No other module may contain
CREATE TABLE statements.  DatabaseManager reads from this file
to initialise SQLite / PostgreSQL schemas and Alembic migrations.

Usage:
    from acas_pro.core.schema import SCHEMA_SQLITE, SCHEMA_POSTGRES, ALL_TABLE_NAMES
"""

from __future__ import annotations

from typing import List

# ---------------------------------------------------------------------------
# SQLite schema  (single string passed to execute())
# ---------------------------------------------------------------------------

SCHEMA_SQLITE: str = """
-- ── Schema version tracking ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

-- ── Core tables ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    account_type TEXT NOT NULL,
    account TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    nickname TEXT,
    email TEXT,
    phone TEXT,
    role TEXT DEFAULT 'user',
    status TEXT DEFAULT 'active',
    region TEXT DEFAULT 'global',
    language TEXT DEFAULT 'zh',
    timezone TEXT DEFAULT 'Asia/Shanghai',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT,
    price REAL DEFAULT 0.0,
    cost REAL DEFAULT 0.0,
    currency TEXT DEFAULT 'CNY',
    stock_quantity INTEGER DEFAULT 0,
    stock_alert_threshold INTEGER DEFAULT 10,
    has_variants INTEGER DEFAULT 0,
    variants TEXT,
    variant_attributes TEXT,
    images TEXT,
    main_image TEXT,
    video_url TEXT,
    weight REAL DEFAULT 0.0,
    length REAL,
    width REAL,
    height REAL,
    category TEXT,
    sub_category TEXT,
    tags TEXT,
    reorder_point INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 100,
    status TEXT DEFAULT 'draft',
    platform_mappings TEXT,
    created_at TEXT,
    updated_at TEXT,
    owner_id TEXT,
    shop_id TEXT,
    total_sales INTEGER DEFAULT 0,
    monthly_sales INTEGER DEFAULT 0,
    weekly_sales INTEGER DEFAULT 0,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    product_id TEXT REFERENCES products(id),
    type TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    status TEXT DEFAULT 'pending',
    platform TEXT,
    metadata TEXT,
    created_at TEXT,
    -- blockchain extensions
    tx_type TEXT,
    from_wallet TEXT,
    to_wallet TEXT,
    fee REAL DEFAULT 0.0,
    blockchain_tx_hash TEXT,
    block_number INTEGER,
    confirmations INTEGER DEFAULT 0,
    settlement_id TEXT,
    confirmed_at TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    product_id TEXT REFERENCES products(id),
    quantity INTEGER NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    shipping_address TEXT,
    created_at TEXT,
    updated_at TEXT,
    -- ecommerce extensions
    platform_order_id TEXT,
    platform TEXT,
    items TEXT,
    subtotal REAL DEFAULT 0.0,
    shipping_fee REAL DEFAULT 0.0,
    discount REAL DEFAULT 0.0,
    tax REAL DEFAULT 0.0,
    payment_status TEXT DEFAULT 'unpaid',
    logistics TEXT,
    buyer_id TEXT,
    buyer_nickname TEXT,
    buyer_message TEXT,
    paid_at TEXT,
    shipped_at TEXT,
    completed_at TEXT,
    shop_id TEXT,
    seller_note TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    id TEXT PRIMARY KEY,
    product_id TEXT REFERENCES products(id),
    quantity INTEGER DEFAULT 0,
    reserved_quantity INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 10,
    reorder_quantity INTEGER DEFAULT 100,
    warehouse_location TEXT,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT,
    nickname TEXT,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    content_count INTEGER DEFAULT 0,
    engagement_rate REAL DEFAULT 0,
    status TEXT DEFAULT 'active',
    credentials TEXT,
    created_at TEXT,
    updated_at TEXT,
    UNIQUE(user_id, platform, account_id)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    name TEXT NOT NULL,
    platform TEXT,
    budget REAL,
    spent REAL DEFAULT 0,
    status TEXT DEFAULT 'draft',
    start_date TEXT,
    end_date TEXT,
    targeting TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS audience_segments (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    name TEXT NOT NULL,
    type TEXT,
    criteria TEXT,
    created_at TEXT,
    updated_at TEXT,
    gender TEXT DEFAULT 'all',
    age_range TEXT,
    geo_targeting TEXT,
    device_targeting TEXT,
    interests TEXT,
    behaviors TEXT,
    custom_tags TEXT,
    source_audience_id TEXT,
    lookalike_ratio REAL,
    estimated_size INTEGER DEFAULT 0,
    estimated_daily_impressions INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS festival_calendar (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    festival_type TEXT,
    date TEXT NOT NULL,
    region TEXT,
    description TEXT,
    marketing_tips TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS content_templates (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    name TEXT NOT NULL,
    content_type TEXT,
    platform TEXT,
    template_content TEXT NOT NULL,
    variables TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_history (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    tokens_used INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    details TEXT,
    ip_address TEXT,
    user_agent TEXT,
    severity TEXT DEFAULT 'info',
    created_at TEXT
);

-- ── Analytics ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS metrics_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metric_type TEXT NOT NULL,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    content_id TEXT,
    value REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    new_followers INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    UNIQUE(date, platform, account_id)
);

CREATE TABLE IF NOT EXISTS data_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    alert_type TEXT NOT NULL,
    platform TEXT,
    account_id TEXT,
    content_id TEXT,
    message TEXT,
    severity TEXT,
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TIMESTAMP,
    acknowledged_by TEXT
);

CREATE TABLE IF NOT EXISTS festivals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_en TEXT,
    festival_type TEXT,
    markets TEXT,
    month INTEGER,
    day INTEGER,
    lunar INTEGER DEFAULT 0,
    floating INTEGER DEFAULT 0,
    floating_rule TEXT,
    importance INTEGER DEFAULT 3,
    duration_days INTEGER DEFAULT 1,
    pre_heat_days INTEGER DEFAULT 7,
    themes TEXT,
    keywords TEXT,
    visual_style TEXT,
    content_tips TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marketing_plans (
    id TEXT PRIMARY KEY,
    festival_id TEXT,
    name TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    target_platforms TEXT,
    target_accounts TEXT,
    content_count INTEGER,
    content_types TEXT,
    budget REAL,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (festival_id) REFERENCES festivals(id)
);

-- ── Avatar ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS digital_avatars (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    style TEXT NOT NULL,
    gender TEXT NOT NULL,
    age_group TEXT NOT NULL,
    appearance TEXT,
    model_path TEXT,
    texture_path TEXT,
    voice_id TEXT,
    idle_animation TEXT,
    talking_animation TEXT,
    gesture_set TEXT,
    created_at TEXT,
    updated_at TEXT,
    owner_id TEXT,
    is_public INTEGER DEFAULT 0,
    usage_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 5.0,
    training_images TEXT,
    training_videos TEXT,
    training_status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS avatar_scenes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    scene_type TEXT,
    background_type TEXT,
    background_path TEXT,
    lighting_preset TEXT,
    camera_angle TEXT,
    camera_distance TEXT,
    avatar_position TEXT,
    avatar_scale REAL,
    props TEXT,
    created_at TEXT,
    owner_id TEXT
);

CREATE TABLE IF NOT EXISTS avatar_render_tasks (
    id TEXT PRIMARY KEY,
    avatar_id TEXT NOT NULL,
    scene_id TEXT,
    script TEXT NOT NULL,
    audio_path TEXT,
    output_path TEXT,
    status TEXT DEFAULT 'pending',
    progress REAL DEFAULT 0.0,
    created_at TEXT,
    completed_at TEXT,
    error_message TEXT
);

-- ── Blockchain ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wallets (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    address TEXT UNIQUE NOT NULL,
    chain_type TEXT DEFAULT 'ethereum',
    balances TEXT,
    encrypted_private_key TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT,
    last_activity TEXT
);

CREATE TABLE IF NOT EXISTS settlements (
    id TEXT PRIMARY KEY,
    settlement_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_type TEXT,
    total_amount REAL NOT NULL,
    currency TEXT DEFAULT 'CNY',
    parties TEXT,
    distribution TEXT,
    status TEXT DEFAULT 'pending',
    blockchain_tx_hash TEXT,
    block_number INTEGER,
    confirmed_at TEXT,
    created_at TEXT,
    settled_at TEXT,
    description TEXT,
    metadata TEXT
);

CREATE TABLE IF NOT EXISTS settlement_details (
    id TEXT PRIMARY KEY,
    settlement_id TEXT NOT NULL,
    party_id TEXT NOT NULL,
    party_type TEXT,
    amount REAL NOT NULL,
    wallet_address TEXT,
    tx_hash TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (settlement_id) REFERENCES settlements(id)
);

-- ── Content ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generated_scripts (
    id TEXT PRIMARY KEY,
    input_text TEXT,
    title TEXT,
    content TEXT,
    style TEXT,
    platform TEXT,
    word_count INTEGER,
    hashtags TEXT,
    hooks TEXT,
    cta TEXT,
    variations TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS trend_items (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    title TEXT,
    author TEXT,
    url TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    publish_time TIMESTAMP,
    tags TEXT,
    content_type TEXT,
    thumbnail_url TEXT,
    viral_score REAL DEFAULT 0,
    efficiency_score REAL DEFAULT 0,
    relevance_score REAL DEFAULT 0,
    transcript TEXT,
    visual_tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Security ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS token_blacklist (
    jti TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token TEXT,
    ip_address TEXT,
    user_agent TEXT,
    last_login TEXT,
    login_count INTEGER DEFAULT 0,
    failed_login_count INTEGER DEFAULT 0,
    locked_until TEXT,
    expires_at REAL,
    created_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ── E-commerce ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shops (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    shop_id_on_platform TEXT,
    shop_url TEXT,
    logo_url TEXT,
    description TEXT,
    contact_name TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    main_category TEXT,
    business_license TEXT,
    credentials TEXT,
    auto_sync INTEGER DEFAULT 1,
    sync_interval INTEGER DEFAULT 15,
    created_at TEXT,
    updated_at TEXT,
    owner_id TEXT,
    last_sync_at TEXT
);

CREATE TABLE IF NOT EXISTS shop_stats (
    shop_id TEXT PRIMARY KEY,
    total_products INTEGER DEFAULT 0,
    total_orders_today INTEGER DEFAULT 0,
    total_orders_month INTEGER DEFAULT 0,
    revenue_today REAL DEFAULT 0.0,
    revenue_month REAL DEFAULT 0.0,
    visitors_today INTEGER DEFAULT 0,
    conversion_rate REAL DEFAULT 0.0,
    rating REAL DEFAULT 5.0,
    updated_at TEXT,
    FOREIGN KEY (shop_id) REFERENCES shops(id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    contact_person TEXT,
    contact_phone TEXT,
    contact_email TEXT,
    company_name TEXT,
    business_license TEXT,
    address TEXT,
    main_products TEXT,
    supply_categories TEXT,
    rating REAL DEFAULT 5.0,
    cooperation_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    payment_terms TEXT,
    created_at TEXT,
    owner_id TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS inventory_syncs (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    shop_id TEXT NOT NULL,
    supplier_id TEXT,
    quantity_before INTEGER,
    quantity_after INTEGER,
    quantity_changed INTEGER,
    status TEXT,
    error_message TEXT,
    synced_at TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL,
    items TEXT,
    subtotal REAL DEFAULT 0.0,
    shipping_fee REAL DEFAULT 0.0,
    total_amount REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    created_at TEXT,
    expected_delivery TEXT,
    delivered_at TEXT,
    notes TEXT
);

-- ── Platforms ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS platform_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT,
    nickname TEXT,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    avatar_url TEXT,
    followers INTEGER DEFAULT 0,
    following INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    content_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    phase TEXT DEFAULT 'warmup',
    tags TEXT,
    region TEXT,
    category TEXT,
    risk_score REAL DEFAULT 0,
    last_violation_at TIMESTAMP,
    violation_count INTEGER DEFAULT 0,
    settings TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    UNIQUE(platform, account_id)
);

CREATE TABLE IF NOT EXISTS account_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    date DATE NOT NULL,
    new_content INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    new_followers INTEGER DEFAULT 0,
    unfollows INTEGER DEFAULT 0,
    net_followers INTEGER DEFAULT 0,
    orders INTEGER DEFAULT 0,
    revenue REAL DEFAULT 0,
    commission REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, date)
);

CREATE TABLE IF NOT EXISTS account_login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    ip_address TEXT,
    device_info TEXT,
    location TEXT,
    success INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Publisher ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS publish_tasks (
    id TEXT PRIMARY KEY,
    content_path TEXT NOT NULL,
    content_type TEXT,
    title TEXT,
    description TEXT,
    tags TEXT,
    cover_image TEXT,
    platforms TEXT,
    scheduled_time TIMESTAMP,
    status TEXT DEFAULT 'pending',
    publish_results TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

-- ── Ads ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ad_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_id TEXT NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TEXT,
    status TEXT DEFAULT 'active',
    balance REAL DEFAULT 0.0,
    daily_budget_limit REAL DEFAULT 0.0,
    total_spend_7d REAL DEFAULT 0.0,
    total_spend_30d REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ad_campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    status TEXT NOT NULL,
    objective TEXT NOT NULL,
    conversion_goal TEXT,
    budget_type TEXT NOT NULL,
    budget_amount REAL NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    adsets_data TEXT NOT NULL,
    total_impressions INTEGER DEFAULT 0,
    total_clicks INTEGER DEFAULT 0,
    total_conversions INTEGER DEFAULT 0,
    total_spend REAL DEFAULT 0.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ad_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    adset_id TEXT NOT NULL,
    date TEXT NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend REAL DEFAULT 0.0,
    ctr REAL DEFAULT 0.0,
    cpc REAL DEFAULT 0.0,
    cpm REAL DEFAULT 0.0,
    conversion_rate REAL DEFAULT 0.0,
    cost_per_conversion REAL DEFAULT 0.0,
    UNIQUE(campaign_id, adset_id, date)
);

-- ── Video ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS video_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    width INTEGER DEFAULT 1080,
    height INTEGER DEFAULT 1920,
    fps INTEGER DEFAULT 30,
    duration REAL DEFAULT 0,
    title TEXT,
    description TEXT,
    script TEXT,
    clips TEXT,
    background_music TEXT,
    voice_over TEXT,
    status TEXT DEFAULT 'draft',
    output_path TEXT,
    target_platform TEXT DEFAULT 'douyin'
);

CREATE TABLE IF NOT EXISTS video_materials (
    id TEXT PRIMARY KEY,
    name TEXT,
    material_type TEXT,
    file_path TEXT NOT NULL,
    duration REAL,
    width INTEGER,
    height INTEGER,
    tags TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voice_tasks (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    language TEXT,
    speed REAL DEFAULT 1.0,
    pitch REAL DEFAULT 1.0,
    volume REAL DEFAULT 1.0,
    emotion TEXT,
    output_path TEXT,
    status TEXT DEFAULT 'pending',
    duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS voice_clones (
    id TEXT PRIMARY KEY,
    name TEXT,
    sample_path TEXT NOT NULL,
    voice_profile TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ---------------------------------------------------------------------------
# PostgreSQL schema  (BOOLEAN→INTEGER already removed, CURRENT_TIMESTAMP→NOW)
# ---------------------------------------------------------------------------

SCHEMA_POSTGRES: str = SCHEMA_SQLITE.replace("AUTOINCREMENT", "").replace(
    "CURRENT_TIMESTAMP", "NOW()").replace(
    "datetime('now')", "NOW()"
).replace(
    "TEXT NOT NULL DEFAULT (NOW())", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"
).replace(
    "TEXT NOT NULL", "TEXT NOT NULL"
)


# ---------------------------------------------------------------------------
# Indexes (SQLite & PostgreSQL compatible)
# ---------------------------------------------------------------------------

INDEXES_SQL: str = """
CREATE INDEX IF NOT EXISTS idx_users_account ON users(account);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_metrics_platform ON metrics_data(platform);
CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date);
CREATE INDEX IF NOT EXISTS idx_trend_platform ON trend_items(platform);
CREATE INDEX IF NOT EXISTS idx_trend_viral ON trend_items(viral_score DESC);
CREATE INDEX IF NOT EXISTS idx_trend_time ON trend_items(publish_time DESC);
CREATE INDEX IF NOT EXISTS idx_token_bl_exp ON token_blacklist(expires_at);
CREATE INDEX IF NOT EXISTS idx_account_platform ON platform_accounts(platform);
CREATE INDEX IF NOT EXISTS idx_account_status ON platform_accounts(status);
CREATE INDEX IF NOT EXISTS idx_stats_account ON account_stats(account_id);
"""

# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

ALL_TABLE_NAMES: List[str] = [
    # Core
    "users",
    "products",
    "transactions",
    "orders",
    "inventory",
    "accounts",
    "campaigns",
    "audience_segments",
    "festival_calendar",
    "content_templates",
    "chat_history",
    "audit_logs",
    "sessions",
    # Analytics
    "metrics_data",
    "daily_metrics",
    "data_alerts",
    "festivals",
    "marketing_plans",
    # Avatar
    "digital_avatars",
    "avatar_scenes",
    "avatar_render_tasks",
    # Blockchain
    "wallets",
    "settlements",
    "settlement_details",
    # Content
    "generated_scripts",
    "trend_items",
    # Security
    "token_blacklist",
    "sessions",
    # E-commerce
    "shops",
    "shop_stats",
    "suppliers",
    "inventory_syncs",
    "purchase_orders",
    # Platforms
    "platform_accounts",
    "account_stats",
    "account_login_logs",
    # Publisher
    "publish_tasks",
    # Ads
    "ad_accounts",
    "ad_campaigns",
    "ad_records",
    # Video
    "video_projects",
    "video_materials",
    "voice_tasks",
    "voice_clones",
]

# Conflicts resolved: publisher's platform_accounts merged into the
# platforms/account_manager version (richer schema).
# transactions merged core + blockchain/wallet_manager columns.
# orders merged core + ecommerce/order_manager columns.
# products merged core + ecommerce/product_manager columns.

# ---------------------------------------------------------------------------
# Schema version management
# ---------------------------------------------------------------------------

# Increment this number whenever you add or change tables, columns, or indexes.
CURRENT_SCHEMA_VERSION: int = 1


def get_schema_version(db) -> int:
    """Return the currently applied schema version, or 0 if never initialised."""
    try:
        row = db.fetchone("SELECT MAX(version) as version FROM schema_version")
        return row["version"] if row and row["version"] is not None else 0
    except Exception:
        return 0


def record_migration(db, version: int, description: str = "") -> None:
    """Record that a schema migration has been applied."""
    db.execute(
        "INSERT INTO schema_version (version, applied_at, description) "
        "VALUES (?, datetime('now'), ?)",
        (version, description),
    )
