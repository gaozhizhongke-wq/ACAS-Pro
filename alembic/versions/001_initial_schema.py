"""Initial schema migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Users table
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_type VARCHAR(50) NOT NULL,
            account VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            nickname VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            role VARCHAR(50) DEFAULT 'user',
            status VARCHAR(50) DEFAULT 'active',
            region VARCHAR(50) DEFAULT 'global',
            language VARCHAR(10) DEFAULT 'zh',
            timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Products table
    op.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(500) NOT NULL,
            description TEXT,
            price DECIMAL(10, 2),
            cost DECIMAL(10, 2),
            stock_quantity INTEGER DEFAULT 0,
            category VARCHAR(255),
            tags JSONB,
            status VARCHAR(50) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Transactions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            type VARCHAR(50) NOT NULL,
            amount DECIMAL(15, 2) NOT NULL,
            currency VARCHAR(10) DEFAULT 'CNY',
            status VARCHAR(50) DEFAULT 'pending',
            platform VARCHAR(100),
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Orders table
    op.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id) ON DELETE SET NULL,
            quantity INTEGER NOT NULL,
            total_amount DECIMAL(15, 2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            shipping_address JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Inventory table
    op.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID REFERENCES products(id) ON DELETE CASCADE,
            quantity INTEGER DEFAULT 0,
            reserved_quantity INTEGER DEFAULT 0,
            reorder_point INTEGER DEFAULT 10,
            reorder_quantity INTEGER DEFAULT 100,
            warehouse_location VARCHAR(255),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Platform accounts
    op.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            platform VARCHAR(100) NOT NULL,
            account_id VARCHAR(255) NOT NULL,
            account_name VARCHAR(255),
            followers INTEGER DEFAULT 0,
            engagement_rate DECIMAL(5, 4) DEFAULT 0,
            status VARCHAR(50) DEFAULT 'active',
            credentials JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, platform, account_id)
        )
    """)
    
    # Campaigns
    op.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(500) NOT NULL,
            platform VARCHAR(100),
            budget DECIMAL(15, 2),
            spent DECIMAL(15, 2) DEFAULT 0,
            status VARCHAR(50) DEFAULT 'draft',
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            targeting JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Audience segments
    op.execute("""
        CREATE TABLE IF NOT EXISTS audience_segments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            segment_type VARCHAR(100),
            size INTEGER DEFAULT 0,
            criteria JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Festival calendar
    op.execute("""
        CREATE TABLE IF NOT EXISTS festival_calendar (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            festival_type VARCHAR(100),
            date DATE NOT NULL,
            region VARCHAR(100),
            description TEXT,
            marketing_tips JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Content templates
    op.execute("""
        CREATE TABLE IF NOT EXISTS content_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(255) NOT NULL,
            content_type VARCHAR(100),
            platform VARCHAR(100),
            template_content TEXT NOT NULL,
            variables JSONB,
            usage_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Chat history
    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            session_id VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            model VARCHAR(100),
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Audit logs
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action VARCHAR(255) NOT NULL,
            resource_type VARCHAR(100),
            resource_id VARCHAR(255),
            details JSONB,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_account ON users(account)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_products_user_id ON products(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)")
    
    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    # Apply triggers
    tables_with_updated_at = ['users', 'products', 'orders', 'accounts', 'campaigns', 
                              'audience_segments', 'content_templates']
    for table in tables_with_updated_at:
        op.execute(f"""
            DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table};
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON {table}
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
        """)
    
    print("Initial schema migration completed successfully")


def downgrade():
    # Drop tables in reverse order
    tables = [
        'audit_logs', 'chat_history', 'content_templates', 'festival_calendar',
        'audience_segments', 'campaigns', 'accounts', 'inventory', 'orders',
        'transactions', 'products', 'users'
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    print("Downgrade completed")
