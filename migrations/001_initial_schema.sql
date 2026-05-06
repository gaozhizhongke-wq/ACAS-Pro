# ACAS PostgreSQL Schema Migration
# 迁移脚本 - 从 SQLite 迁移到 PostgreSQL

-- ============================================
-- Users & Authentication
-- ============================================

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    role VARCHAR(20) DEFAULT 'user',
    status VARCHAR(20) DEFAULT 'active',
    email_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_status ON users(status);

-- ============================================
-- Sessions & Tokens
-- ============================================

CREATE TABLE sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_expires ON sessions(expires_at);

CREATE TABLE audit_logs (
    log_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    session_id VARCHAR(64),
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- ============================================
-- Social Media Accounts
-- ============================================

CREATE TABLE accounts (
    account_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100),
    account_id_ext VARCHAR(100),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'active',
    followers_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_accounts_user ON accounts(user_id);
CREATE INDEX idx_accounts_platform ON accounts(platform);

-- ============================================
-- Content & Publishing
-- ============================================

CREATE TABLE content (
    content_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    body TEXT,
    content_type VARCHAR(20),
    tags TEXT[],
    status VARCHAR(20) DEFAULT 'draft',
    published_at TIMESTAMP,
    platforms TEXT[],
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_user ON content(user_id);
CREATE INDEX idx_content_status ON content(status);

CREATE TABLE scheduled_posts (
    post_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    content_id INTEGER REFERENCES content(content_id) ON DELETE CASCADE,
    account_id INTEGER REFERENCES accounts(account_id) ON DELETE CASCADE,
    scheduled_at TIMESTAMP NOT NULL,
    posted_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'scheduled',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduled_user ON scheduled_posts(user_id);
CREATE INDEX idx_scheduled_time ON scheduled_posts(scheduled_at);

-- ============================================
-- Analytics & Forecasting
-- ============================================

CREATE TABLE forecasts (
    forecast_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    model_type VARCHAR(20),
    horizon_days INTEGER,
    predictions JSONB,
    metrics JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_forecasts_user ON forecasts(user_id);

-- ============================================
-- Inventory & Products
-- ============================================

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    sku VARCHAR(100) UNIQUE,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(50),
    price DECIMAL(10,2),
    cost DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    reorder_point INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_user ON products(user_id);
CREATE INDEX idx_products_sku ON products(sku);

CREATE TABLE inventory_logs (
    log_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
    change_type VARCHAR(20),
    quantity_change INTEGER,
    quantity_after INTEGER,
    reference_id VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_inventory_product ON inventory_logs(product_id);

-- ============================================
-- Ads & Campaigns
-- ============================================

CREATE TABLE campaigns (
    campaign_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    platform VARCHAR(20),
    name VARCHAR(255),
    budget DECIMAL(12,2),
    daily_budget DECIMAL(12,2),
    status VARCHAR(20) DEFAULT 'draft',
    start_date DATE,
    end_date DATE,
    targeting JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_campaigns_user ON campaigns(user_id);

CREATE TABLE ad_metrics (
    metric_id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    campaign_id INTEGER REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend DECIMAL(12,2) DEFAULT 0,
    cpc DECIMAL(10,2),
    cpm DECIMAL(10,2),
    cpa DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ad_metrics_campaign ON ad_metrics(campaign_id);
CREATE INDEX idx_ad_metrics_date ON ad_metrics(date);

-- ============================================
-- Intelligence & Monitoring
-- ============================================

CREATE TABLE news_articles (
    article_id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    title TEXT,
    url TEXT UNIQUE,
    source VARCHAR(100),
    sentiment VARCHAR(10),
    sentiment_score DECIMAL(5,4),
    keywords TEXT[],
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_news_user ON news_articles(user_id);
CREATE INDEX idx_news_sentiment ON news_articles(sentiment);

-- ============================================
-- Functions & Triggers
-- ============================================

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables with updated_at
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER content_updated_at
    BEFORE UPDATE ON content
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();