# ACAS Pro - Performance Testing

## 🚀 Quick Start

### 1. Start the Application

```bash
# Using Docker Compose
docker-compose up -d app db redis

# Or local development
python -m acas_pro.web
```

### 2. Run Performance Test

```bash
# Default: 100 users, 60 seconds
./performance-test.sh

# Custom: 1000 users, 5 minutes
./performance-test.sh 1000 300

# Custom host
./performance-test.sh 100 60 http://your-server.com
```

### 3. View Results

Results are saved to `results/`:
- `acas_pro_*_stats.csv` - Statistics
- `acas_pro_*_failures.csv` - Failures
- `report_*.html` - HTML report

## 📊 Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| **RPS** | 1000+ | Requests per second |
| **Latency (p95)** | < 200ms | 95th percentile response time |
| **Latency (p99)** | < 500ms | 99th percentile response time |
| **Error Rate** | < 0.1% | Failed requests percentage |
| **CPU Usage** | < 70% | Server CPU utilization |
| **Memory** | < 80% | Server memory usage |

## 🔧 Test Scenarios

### Scenario 1: Health Check Load
- 1000 concurrent users
- Only `/api/health` endpoint
- Target: 5000+ RPS

### Scenario 2: Mixed API Load
- 500 concurrent users
- Mix of: health, dashboard, products, accounts
- Target: 1000+ RPS, p95 < 200ms

### Scenario 3: Authenticated Load
- 200 concurrent users
- All authenticated endpoints
- Target: 500+ RPS, p95 < 300ms

## 🛠️ Troubleshooting

### High Error Rate
- Check database connection pool
- Increase `max_connections` in PostgreSQL
- Check Redis connection limits

### High Latency
- Enable database query caching
- Add Redis caching layer
- Optimize slow queries

### Memory Issues
- Check for memory leaks
- Monitor garbage collection
- Increase container memory limits

## 📈 Continuous Monitoring

Prometheus metrics available at:
- `http://localhost:9090` - Prometheus UI
- `http://localhost:3000` - Grafana Dashboards

Key dashboards:
- Request rate and latency
- Database performance
- Cache hit rates
- LLM API usage and costs
