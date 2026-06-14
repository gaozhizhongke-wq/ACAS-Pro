# ACAS Pro - Production Deployment Guide

## 🔒 SSL/HTTPS Configuration

### Option 1: Let's Encrypt (Production)

```bash
# Set environment variables
export ENVIRONMENT=production
export DOMAIN=your-domain.com
export ADMIN_EMAIL=admin@your-domain.com

# Run SSL setup
chmod +x setup-ssl.sh
./setup-ssl.sh

# Start services
docker-compose up -d nginx
```

### Option 2: Self-Signed (Development)

```bash
export ENVIRONMENT=development
export DOMAIN=localhost
./setup-ssl.sh
```

### Option 3: Cloudflare (Recommended for China)

1. Point domain to Cloudflare
2. Enable "Full (Strict)" SSL mode
3. Use Cloudflare Origin Certificates
4. Install certificate in `ssl/` directory

## 🔑 Secret Management

### Docker Secrets (Production)

```yaml
# docker-compose.yml
secrets:
  secret_key:
    file: ./secrets/secret_key.txt
  db_password:
    file: ./secrets/db_password.txt

services:
  app:
    secrets:
      - secret_key
      - db_password
    environment:
      - SECRET_KEY_FILE=/run/secrets/secret_key
      - DB_PASSWORD_FILE=/run/secrets/db_password
```

### Environment Variables (Development)

```bash
# .env file
SECRET_KEY=your-secret-key-32-chars-long
DB_PASSWORD=development-password
DEEPSEEK_API_KEY=your-api-key
```

## 📊 Monitoring Setup

### Prometheus + Grafana

Already configured in `docker-compose.yml`:

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

### Key Metrics

- Request rate (QPS)
- Response time (p50, p95, p99)
- Error rate
- Database connections
- Cache hit rate
- LLM API latency

## 🚀 Deployment Checklist

- [ ] SSL certificate installed
- [ ] Secrets configured (not in git)
- [ ] Database migrated
- [ ] Health check passing
- [ ] Monitoring dashboards created
- [ ] Backup strategy configured
- [ ] Load balancer configured (if multi-node)

## 🔄 CI/CD Pipeline

GitHub Actions workflow in `.github/workflows/ci.yml`:

1. **Lint**: ruff + mypy
2. **Test**: pytest with coverage
3. **Build**: Docker image
4. **Deploy**: SSH to server + docker-compose up

## 📞 Support

- Issues: https://github.com/gaozhizhongke-wq/ACAS-Pro/issues
- Documentation: https://github.com/gaozhizhongke-wq/ACAS-Pro/wiki
