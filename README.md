# ACAS Pro - Automatic Customer Acquisition System

[![Version](https://img.shields.io/badge/version-4.0.0-blue.svg)](https://github.com/acas-pro/acas-pro)
[![Python](https://img.shields.io/badge/python-3.11%2B-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0%2B-orange.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)]()

> Production-grade automated customer acquisition platform with AI-powered content generation, multi-platform publishing, and comprehensive analytics.

## ✨ Features

- **AI-Powered Content**: Integration with OpenAI, Anthropic, Kimi, DeepSeek, Qwen
- **Multi-Platform Publishing**: Support for major social media and e-commerce platforms
- **Advanced Analytics**: Real-time data monitoring, trend analysis, forecasting
- **Security-First**: JWT authentication, rate limiting, input validation, security headers
- **Production Ready**: Comprehensive health checks, structured logging, request tracing

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (recommended for production)
- Redis (optional, for distributed rate limiting)

### Installation

```bash
# Clone repository
git clone https://github.com/acas-pro/acas-pro.git
cd acas-pro

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
python -c "from acas_pro.core.database import db; db.init_database()"

# Start application
python web_app.py
```

### Environment Variables

```bash
# Required
SECRET_KEY=your-secret-key-here  # Generate: python -c "import secrets; print(secrets.token_urlsafe(48))"
ACAS_ENCRYPTION_SALT=your-salt-here  # Generate: python -c "import secrets; print(secrets.token_hex(32))"

# Database (SQLite for dev, PostgreSQL for production)
DATABASE_URL=sqlite:///data/acas.db
# DATABASE_URL=postgresql://user:pass@localhost/acas_pro

# LLM Provider (at least one required)
DEEPSEEK_API_KEY=your-api-key
# OPENAI_API_KEY=your-api-key
# ANTHROPIC_API_KEY=your-api-key

# Optional
ACAS_ENV=production  # development, staging, production
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## 📚 API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:5000/api/docs
- **OpenAPI Spec**: http://localhost:5000/api/openapi.json

### Authentication

All API endpoints (except `/api/health`, `/api/auth/login`, `/api/auth/register`) require authentication via Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" http://localhost:5000/api/auth/me
```

### Key Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/health` | GET | Health check | No |
| `/api/auth/register` | POST | User registration | No |
| `/api/auth/login` | POST | User login | No |
| `/api/auth/me` | GET | Current user info | Yes |
| `/api/llm/chat` | POST | Chat with LLM | Yes |
| `/api/dashboard/stats` | GET | Dashboard statistics | Yes |

## 🏗️ Architecture

```
acas_pro/
├── core/               # Core utilities
│   ├── config.py       # Configuration management
│   ├── database.py     # Database abstraction
│   ├── security.py     # Authentication & encryption
│   └── logging.py      # Structured logging
├── services/           # Business logic
│   └── user_service.py # User management
├── web/                # Web layer (new)
│   ├── middleware.py   # Request tracing, error handling
│   ├── health.py       # Health checks
│   └── api_spec.py     # OpenAPI documentation
├── llm/                # LLM integration
├── analytics/          # Data analytics
└── publishers/         # Platform publishers
```

## 🔒 Security

### Implemented Protections

- **JWT Authentication**: Short-lived access tokens (15 min) with refresh tokens
- **Rate Limiting**: Login (20/10min), Register (10/10min)
- **Password Policy**: Min 8 chars, uppercase, lowercase, number, special char
- **Input Validation**: SQL injection and XSS pattern detection
- **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **Request Tracing**: X-Request-ID correlation for audit trails

### Production Checklist

- [ ] Change default SECRET_KEY
- [ ] Set ACAS_ENCRYPTION_SALT
- [ ] Use PostgreSQL instead of SQLite
- [ ] Configure HTTPS with valid SSL certificate
- [ ] Set up Redis for distributed rate limiting
- [ ] Enable HSTS in nginx
- [ ] Configure log aggregation (ELK/Loki)
- [ ] Set up monitoring (Prometheus/Grafana)

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/acas_pro --cov-report=html

# Run specific test file
pytest tests/test_auth.py
```

## 🚢 Deployment

### Docker

```bash
# Build image
docker build -t acas-pro:latest .

# Run container
docker run -d \
  -p 5000:5000 \
  -e SECRET_KEY=your-secret \
  -e DATABASE_URL=postgresql://... \
  acas-pro:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Kubernetes

See `k8s/` directory for deployment manifests.

## 📊 Monitoring

### Health Checks

```bash
curl http://localhost:5000/api/health
```

Response includes:
- Database connectivity status
- Configuration validation
- Disk space monitoring
- Response times for each check

### Logs

Structured JSON logs with request correlation:

```json
{
  "timestamp": "2026-05-10T13:53:27Z",
  "level": "INFO",
  "request_id": "a1b2c3d4e5f6",
  "method": "POST",
  "path": "/api/auth/login",
  "status": 200,
  "duration_ms": 45.23
}
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

### Code Standards

- Follow PEP 8 style guide
- Add type hints for function signatures
- Write docstrings for public APIs
- Maintain test coverage > 80%

## 📄 License

Proprietary - All rights reserved.

## 🆘 Support

- **Documentation**: `/api/docs` (when running)
- **Issues**: Internal issue tracker
- **Email**: support@acas-pro.com

---

**ACAS Pro** - Empowering businesses with intelligent customer acquisition.
