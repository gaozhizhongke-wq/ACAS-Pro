#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Production Setup Script
One-command production deployment
"""

import os
import sys
import subprocess
import secrets
import string
from pathlib import Path


def generate_secret(length=64):
    """生成安全密钥"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def check_dependencies():
    """检查依赖"""
    print("="*60)
    print("Step 1: Checking Dependencies")
    print("="*60)
    
    required = {
        'docker': 'Docker',
        'docker-compose': 'Docker Compose',
        'python': 'Python 3.11+'
    }
    
    missing = []
    for cmd, name in required.items():
        result = subprocess.run(
            ['which' if os.name != 'nt' else 'where', cmd],
            capture_output=True
        )
        if result.returncode != 0:
            missing.append(name)
            print(f"  [MISSING] {name}")
        else:
            print(f"  [OK] {name}")
    
    if missing:
        print(f"\nPlease install: {', '.join(missing)}")
        return False
    
    return True


def setup_environment():
    """设置环境变量"""
    print("\n" + "="*60)
    print("Step 2: Setting up Environment")
    print("="*60)
    
    env_file = Path('.env')
    
    if env_file.exists():
        print("  [INFO] .env file already exists")
        return True
    
    # Generate secrets
    db_password = generate_secret(32)
    jwt_secret = generate_secret(64)
    encryption_key = generate_secret(32)
    vault_token = generate_secret(32)
    grafana_password = generate_secret(16)
    
    env_content = f"""# ACAS Pro - Production Environment
# Generated automatically - DO NOT COMMIT

# Database
DB_PASSWORD={db_password}

# Security
JWT_SECRET_KEY={jwt_secret}
ENCRYPTION_KEY={encryption_key}

# Vault
VAULT_TOKEN={vault_token}

# Monitoring
GRAFANA_PASSWORD={grafana_password}

# Environment
ENV=production
LOG_LEVEL=INFO
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("  [OK] .env file created with secure secrets")
    print("  [WARN] Keep .env file secure and never commit it")
    
    return True


def setup_directories():
    """创建必要目录"""
    print("\n" + "="*60)
    print("Step 3: Creating Directories")
    print("="*60)
    
    dirs = [
        'logs',
        'data',
        'certs',
        'database/init',
        'vault/config',
        'monitoring/grafana-dashboards'
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"  [OK] {d}/")
    
    return True


def generate_ssl_certs():
    """生成SSL证书"""
    print("\n" + "="*60)
    print("Step 4: SSL Certificates")
    print("="*60)
    
    cert_dir = Path('certs')
    
    if (cert_dir / 'server.crt').exists():
        print("  [INFO] SSL certificates already exist")
        return True
    
    print("  Generating self-signed certificates...")
    
    # Generate private key
    subprocess.run([
        'openssl', 'genrsa', '-out', str(cert_dir / 'server.key'), '4096'
    ], check=True, capture_output=True)
    
    # Generate certificate
    subprocess.run([
        'openssl', 'req', '-new', '-x509',
        '-key', str(cert_dir / 'server.key'),
        '-out', str(cert_dir / 'server.crt'),
        '-days', '365',
        '-subj', '/CN=acas-pro.com'
    ], check=True, capture_output=True)
    
    print("  [OK] SSL certificates generated")
    print("  [WARN] Using self-signed certs - replace with real certs for production")
    
    return True


def setup_database():
    """初始化数据库"""
    print("\n" + "="*60)
    print("Step 5: Database Initialization")
    print("="*60)
    
    init_sql = """
-- ACAS Pro - Database Initialization

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'operator',
    tenant_id VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    mfa_enabled BOOLEAN DEFAULT false,
    mfa_secret VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES users(id),
    user_email VARCHAR(255),
    action VARCHAR(100),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    status VARCHAR(50),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    hash_chain VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- Insert admin user (password: Admin123!)
INSERT INTO users (email, password_hash, name, role)
VALUES (
    'admin@acas-pro.com',
    crypt('Admin123!', gen_salt('bf')),
    'System Administrator',
    'admin'
) ON CONFLICT (email) DO NOTHING;
"""
    
    init_file = Path('database/init/01_init.sql')
    with open(init_file, 'w') as f:
        f.write(init_sql)
    
    print(f"  [OK] Database init script: {init_file}")
    
    return True


def start_services():
    """启动服务"""
    print("\n" + "="*60)
    print("Step 6: Starting Services")
    print("="*60)
    
    print("  Starting Docker Compose...")
    
    result = subprocess.run(
        ['docker-compose', 'up', '-d'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  [ERROR] Failed to start services:")
        print(result.stderr)
        return False
    
    print("  [OK] Services started")
    print("\n  Services:")
    print("    - API: http://localhost:8000")
    print("    - Grafana: http://localhost:3000")
    print("    - Prometheus: http://localhost:9090")
    print("    - Vault: http://localhost:8200")
    
    return True


def health_check():
    """健康检查"""
    print("\n" + "="*60)
    print("Step 7: Health Check")
    print("="*60)
    
    import time
    import requests
    
    services = {
        'API': 'http://localhost:8000/health',
        'Grafana': 'http://localhost:3000/api/health',
        'Prometheus': 'http://localhost:9090/-/healthy'
    }
    
    max_retries = 30
    for i in range(max_retries):
        all_healthy = True
        
        for name, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"  [OK] {name}")
                else:
                    print(f"  [WAIT] {name} - {response.status_code}")
                    all_healthy = False
            except Exception as e:
                print(f"  [WAIT] {name} - not ready")
                all_healthy = False
        
        if all_healthy:
            print("\n  [SUCCESS] All services are healthy!")
            return True
        
        time.sleep(2)
    
    print("\n  [WARNING] Some services may not be ready yet")
    return True


def print_summary():
    """打印摘要"""
    print("\n" + "="*60)
    print("ACAS Pro - Production Setup Complete")
    print("="*60)
    
    print("\n[Access URLs]")
    print("  API:        http://localhost:8000")
    print("  Grafana:    http://localhost:3000 (admin / see .env)")
    print("  Prometheus: http://localhost:9090")
    print("  Vault:      http://localhost:8200")
    
    print("\n[Useful Commands]")
    print("  View logs:   docker-compose logs -f")
    print("  Stop:        docker-compose down")
    print("  Restart:     docker-compose restart")
    print("  Update:      docker-compose pull && docker-compose up -d")
    
    print("\n[Security Notes]")
    print("  1. Change default passwords in .env")
    print("  2. Replace self-signed SSL certificates")
    print("  3. Configure firewall rules")
    print("  4. Enable audit logging")
    
    print("\n" + "="*60)


def main():
    """主函数"""
    print("\n" + "="*60)
    print("ACAS Pro - Production Setup")
    print("="*60)
    
    steps = [
        ("Check Dependencies", check_dependencies),
        ("Setup Environment", setup_environment),
        ("Create Directories", setup_directories),
        ("Generate SSL Certs", generate_ssl_certs),
        ("Setup Database", setup_database),
        ("Start Services", start_services),
        ("Health Check", health_check)
    ]
    
    for name, func in steps:
        try:
            if not func():
                print(f"\n[ERROR] Step '{name}' failed")
                sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Step '{name}' failed: {e}")
            sys.exit(1)
    
    print_summary()


if __name__ == '__main__':
    main()
