# Extracted CREATE TABLE IF NOT EXISTS Statements from ACAS-Pro

## === analytics/data_monitor.py ===

```sql
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
    severity TEXT,  -- info, warning, critical
    acknowledged BOOLEAN DEFAULT 0,
    acknowledged_at TIMESTAMP,
    acknowledged_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_metrics_time ON metrics_data(timestamp);

CREATE INDEX IF NOT EXISTS idx_metrics_platform ON metrics_data(platform);

CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date);
```

## === analytics/festival_calendar.py ===

```sql
CREATE TABLE IF NOT EXISTS festivals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_en TEXT,
    festival_type TEXT,
    markets TEXT,  -- JSON array
    month INTEGER,
    day INTEGER,
    lunar BOOLEAN DEFAULT 0,
    floating BOOLEAN DEFAULT 0,
    floating_rule TEXT,
    importance INTEGER DEFAULT 3,
    duration_days INTEGER DEFAULT 1,
    pre_heat_days INTEGER DEFAULT 7,
    themes TEXT,  -- JSON array
    keywords TEXT,  -- JSON array
    visual_style TEXT,
    content_tips TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS marketing_plans (
    id TEXT PRIMARY KEY,
    festival_id TEXT,
    name TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    target_platforms TEXT,  -- JSON array
    target_accounts TEXT,  -- JSON array
    content_count INTEGER,
    content_types TEXT,  -- JSON array
    budget REAL,
    status TEXT DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (festival_id) REFERENCES festivals(id)
);
```

## === avatar/avatar_engine.py ===

```sql
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
```

## === blockchain/settlement_engine.py ===

```sql
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
```

## === blockchain/wallet_manager.py ===

```sql
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

CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    tx_type TEXT NOT NULL,
    from_wallet TEXT,
    to_wallet TEXT,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USDT',
    fee REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending',
    blockchain_tx_hash TEXT,
    block_number INTEGER,
    confirmations INTEGER DEFAULT 0,
    settlement_id TEXT,
    description TEXT,
    created_at TEXT,
    confirmed_at TEXT
);
```

## === content/script_generator.py ===

```sql
CREATE TABLE IF NOT EXISTS generated_scripts (
    id TEXT PRIMARY KEY,
    input_text TEXT,
    title TEXT,
    content TEXT,
    style TEXT,
    platform TEXT,
    word_count INTEGER,
    hashtags TEXT,  -- JSON array
    hooks TEXT,  -- JSON array
    cta TEXT,
    variations TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## === content/trend_monitor.py ===

```sql
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
    tags TEXT,  -- JSON array
    content_type TEXT,
    thumbnail_url TEXT,
    viral_score REAL DEFAULT 0,
    efficiency_score REAL DEFAULT 0,
    relevance_score REAL DEFAULT 0,
    transcript TEXT,
    visual_tags TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trend_platform ON trend_items(platform);

CREATE INDEX IF NOT EXISTS idx_trend_viral ON trend_items(viral_score DESC);

CREATE INDEX IF NOT EXISTS idx_trend_time ON trend_items(publish_time DESC);
```

## === core/security.py ===

```sql
CREATE TABLE IF NOT EXISTS token_blacklist (
    jti TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_token_bl_exp ON token_blacklist (expires_at);
```

Note: core/security.py also references a `sessions` table used by SessionManager (INSERT INTO sessions), but no explicit CREATE TABLE IF NOT EXISTS for sessions is in this file. It's likely defined elsewhere (e.g., in database.py or a migration).

## === ecommerce/order_manager.py ===

```sql
CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    platform_order_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    items TEXT,
    subtotal REAL DEFAULT 0.0,
    shipping_fee REAL DEFAULT 0.0,
    discount REAL DEFAULT 0.0,
    tax REAL DEFAULT 0.0,
    total_amount REAL DEFAULT 0.0,
    status TEXT DEFAULT 'pending_payment',
    payment_status TEXT DEFAULT 'unpaid',
    shipping_address TEXT,
    logistics TEXT,
    buyer_id TEXT,
    buyer_nickname TEXT,
    buyer_message TEXT,
    created_at TEXT,
    paid_at TEXT,
    shipped_at TEXT,
    completed_at TEXT,
    shop_id TEXT,
    seller_note TEXT
);
```

## === ecommerce/product_manager.py ===

```sql
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    sub_category TEXT,
    price REAL DEFAULT 0.0,
    original_price REAL,
    cost_price REAL,
    stock INTEGER DEFAULT 0,
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
    status TEXT DEFAULT 'draft',
    platform_mappings TEXT,
    created_at TEXT,
    updated_at TEXT,
    owner_id TEXT,
    shop_id TEXT,
    total_sales INTEGER DEFAULT 0,
    monthly_sales INTEGER DEFAULT 0,
    weekly_sales INTEGER DEFAULT 0
);
```

## === ecommerce/shop_manager.py ===

```sql
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
```

## === ecommerce/supply_chain.py ===

```sql
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
```

## === platforms/account_manager.py ===

```sql
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
    tags TEXT,  -- JSON array
    region TEXT,
    category TEXT,
    risk_score REAL DEFAULT 0,
    last_violation_at TIMESTAMP,
    violation_count INTEGER DEFAULT 0,
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
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_account_platform ON platform_accounts(platform);

CREATE INDEX IF NOT EXISTS idx_account_status ON platform_accounts(status);

CREATE INDEX IF NOT EXISTS idx_stats_account ON account_stats(account_id);
```

## === publisher/publish_manager.py ===

```sql
CREATE TABLE IF NOT EXISTS publish_tasks (
    id TEXT PRIMARY KEY,
    content_path TEXT NOT NULL,
    content_type TEXT,
    title TEXT,
    description TEXT,
    tags TEXT,  -- JSON array
    cover_image TEXT,
    platforms TEXT,  -- JSON array
    scheduled_time TIMESTAMP,
    status TEXT DEFAULT 'pending',
    publish_results TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3
);

CREATE TABLE IF NOT EXISTS platform_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_id TEXT NOT NULL,
    account_name TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    settings TEXT,  -- JSON
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## === video/video_maker.py ===

```sql
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
    clips TEXT,  -- JSON
    background_music TEXT,
    voice_over TEXT,
    status TEXT DEFAULT 'draft',
    output_path TEXT,
    target_platform TEXT DEFAULT 'douyin'
);

CREATE TABLE IF NOT EXISTS video_materials (
    id TEXT PRIMARY KEY,
    name TEXT,
    material_type TEXT,  -- video/image/audio
    file_path TEXT NOT NULL,
    duration REAL,
    width INTEGER,
    height INTEGER,
    tags TEXT,  -- JSON array
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## === video/voice_synthesis.py ===

```sql
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
    status TEXT DEFAULT 'pending',  -- pending/processing/completed/failed
    duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS voice_clones (
    id TEXT PRIMARY KEY,
    name TEXT,
    sample_path TEXT NOT NULL,
    voice_profile TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## === ads/ad_manager.py ===

```sql
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
```

## === ads/audience_targeting.py ===

No explicit `CREATE TABLE IF NOT EXISTS audience_segments` statement found in this file. The `_ensure_table` method only uses `ALTER TABLE` to add columns to an existing `audience_segments` table, which is presumably created by DatabaseManager's schema initialization elsewhere.

---

## Summary Table

| File | Tables | Indexes |
|------|--------|---------|
| analytics/data_monitor.py | metrics_data, daily_metrics, data_alerts | idx_metrics_time, idx_metrics_platform, idx_daily_metrics_date |
| analytics/festival_calendar.py | festivals, marketing_plans | — |
| avatar/avatar_engine.py | digital_avatars, avatar_scenes, avatar_render_tasks | — |
| blockchain/settlement_engine.py | settlements, settlement_details | — |
| blockchain/wallet_manager.py | wallets, transactions | — |
| content/script_generator.py | generated_scripts | — |
| content/trend_monitor.py | trend_items | idx_trend_platform, idx_trend_viral, idx_trend_time |
| core/security.py | token_blacklist | idx_token_bl_exp |
| ecommerce/order_manager.py | orders | — |
| ecommerce/product_manager.py | products | — |
| ecommerce/shop_manager.py | shops, shop_stats | — |
| ecommerce/supply_chain.py | suppliers, inventory_syncs, purchase_orders | — |
| platforms/account_manager.py | platform_accounts, account_stats, account_login_logs | idx_account_platform, idx_account_status, idx_stats_account |
| publisher/publish_manager.py | publish_tasks, platform_accounts | — |
| video/video_maker.py | video_projects, video_materials | — |
| video/voice_synthesis.py | voice_tasks, voice_clones | — |
| ads/ad_manager.py | ad_accounts, ad_campaigns, ad_records | — |
| ads/audience_targeting.py | (none — table created by DatabaseManager) | — |

**Total: 34 CREATE TABLE statements + 9 CREATE INDEX statements across 18 files.**

Note: `publisher/publish_manager.py` defines a `platform_accounts` table that differs from the one in `platforms/account_manager.py`. This is a naming conflict that may cause issues if both modules share the same database.
