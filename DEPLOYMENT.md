# ACAS Pro - Deployment Guide

## Quick Start (Production)

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Nginx
- Docker & Docker Compose (optional)

### 2. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd ACAS-Pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file:

```bash
# Required
ENVIRONMENT=production
SECRET_KEY=<generate-with-python-secrets>

# Database (PostgreSQL required for production)
DATABASE_URL=postgresql://user:password@localhost:5432/acas

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM API Keys (at least one)
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: OAuth
QQ_APP_ID=...
WECHAT_APP_ID=...

# Optional: Alert webhooks
DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=...
WECOM_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=...
```

Generate secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 4. Database Setup

```bash
# Create database
createdb acas

# Run migrations
cd alembic
alembic upgrade head
```

### 5. Start Production Server

```bash
# Option 1: Direct (with waitress)
python wsgi.py

# Option 2: Using start script
python start_production.py

# Option 3: Docker Compose
docker-compose up -d
```

### 6. Nginx Configuration

```bash
# Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/acas
sudo ln -s /etc/nginx/sites-available/acas /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL/TLS (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com
```

---

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t acas-pro:latest .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f app

# Scale app instances
docker-compose up -d --scale app=3
```

---

## Health Checks

```bash
# Application health
curl http://localhost:5000/api/health

# Database health
curl http://localhost:5000/api/health | jq '.database'
```

---

## Monitoring

### Prometheus Metrics

Endpoint: `http://localhost:5000/metrics`

Key metrics:
- `acas_http_requests_total` - HTTP request count
- `acas_http_request_duration_seconds` - Request latency
- `acas_llm_requests_total` - LLM API calls
- `acas_active_users` - Active user count

### Grafana Dashboard

Access: `http://localhost:3000` (if using docker-compose)

Default credentials: admin/admin

---

## Backup & Recovery

### Database Backup

```bash
# Automated daily backup
pg_dump acas > backup/acas_$(date +%Y%m%d).sql

# Restore
psql acas < backup/acas_20240101.sql
```

### Docker Volume Backup

```bash
# Backup volumes
docker run --rm -v acas_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .

# Restore
docker run --rm -v acas_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres_backup.tar.gz -C /data
```

---

## Troubleshooting

### Server won't start

1. Check `.env` file exists and SECRET_KEY is set
2. Verify database connection: `psql $DATABASE_URL -c "SELECT 1"`
3. Check logs: `tail -f logs/acas.log`

### Database connection errors

1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check connection string format
3. Ensure database exists: `psql -l | grep acas`

### High memory usage

1. Reduce connection pool size in `wsgi.py`
2. Enable swap: `sudo swapon /swapfile`
3. Add memory limits in docker-compose

---

## Security Checklist

- [ ] SECRET_KEY changed from default
- [ ] HTTPS enabled with valid certificate
- [ ] Database using PostgreSQL (not SQLite)
- [ ] Redis password set
- [ ] Firewall configured (only 80/443 open)
- [ ] Regular backups configured
- [ ] Log rotation enabled
- [ ] Security headers verified (CSP, HSTS)
