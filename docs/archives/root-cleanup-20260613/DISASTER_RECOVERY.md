# ACAS Pro - Disaster Recovery Plan

## Recovery Objectives

- **RPO (Recovery Point Objective)**: 1 hour (maximum data loss)
- **RTO (Recovery Time Objective)**: 4 hours (maximum downtime)

## Backup Strategy

### Database Backups

#### Automated Daily Backups
```bash
#!/bin/bash
# /opt/acas/backup/backup.sh

BACKUP_DIR="/backup/acas"
DB_NAME="acas"
RETENTION_DAYS=30

# Create backup
pg_dump -Fc $DB_NAME > "$BACKUP_DIR/acas_$(date +%Y%m%d_%H%M%S).dump"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/acas_$(date +%Y%m%d_%H%M%S).dump" s3://acas-backups/

# Clean old backups
find $BACKUP_DIR -name "acas_*.dump" -mtime +$RETENTION_DAYS -delete
```

#### Continuous WAL Archiving
```ini
# postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
max_wal_size = 1GB
```

### File Backups

```bash
# Configuration backup
tar czf /backup/acas_config_$(date +%Y%m%d).tar.gz \
  .env \
  nginx.conf \
  docker-compose.yml

# Application code (from git)
git clone --depth 1 <repository> /backup/acas-code-$(date +%Y%m%d)
```

## Recovery Procedures

### Scenario 1: Database Corruption

```bash
# 1. Stop application
docker-compose stop app

# 2. Drop corrupted database
dropdb acas

# 3. Create new database
createdb acas

# 4. Restore from backup
pg_restore -d acas /backup/acas_20240101_000000.dump

# 5. Restart application
docker-compose start app

# 6. Verify
curl http://localhost:5000/api/health
```

### Scenario 2: Complete Server Failure

```bash
# 1. Provision new server
# - Same OS version
# - Same or better specs
# - Network configuration

# 2. Install dependencies
apt update && apt install -y docker docker-compose nginx

# 3. Restore configuration
scp backup-server:/backup/acas_config_*.tar.gz /tmp/
tar xzf /tmp/acas_config_*.tar.gz -C /opt/acas/

# 4. Clone application
git clone <repository> /opt/acas

# 5. Restore database
scp backup-server:/backup/acas_*.dump /tmp/
docker-compose up -d db
sleep 10
docker-compose exec -T db pg_restore -U acas -d acas < /tmp/acas_*.dump

# 6. Start services
docker-compose up -d

# 7. Verify
curl http://localhost:5000/api/health
```

### Scenario 3: Application Bug (Rollback)

```bash
# 1. Identify last known good version
git log --oneline

# 2. Checkout stable version
git checkout <stable-commit>

# 3. Restart application
docker-compose down
docker-compose up -d --build

# 4. Verify
curl http://localhost:5000/api/health
```

## Failover Procedures

### Primary-Replica Failover

```bash
# On replica server:
# 1. Promote replica to primary
pg_ctl promote

# 2. Update application configuration
# Change DATABASE_URL to point to replica

# 3. Restart application
docker-compose restart app
```

### Load Balancer Failover

```bash
# If using multiple app instances:
# 1. Remove failed instance from load balancer
# 2. Traffic automatically routes to healthy instances
# 3. Replace failed instance
# 4. Add new instance back to load balancer
```

## Testing

### Monthly DR Drill

1. **Backup Restoration Test**
   ```bash
   # Create test environment
   createdb acas_test
   pg_restore -d acas_test /backup/latest.dump
   
   # Verify data integrity
   psql acas_test -c "SELECT COUNT(*) FROM users;"
   ```

2. **Failover Test**
   ```bash
   # Simulate primary failure
   docker-compose stop db
   
   # Execute failover procedure
   # Verify application continues working
   ```

### Quarterly Full DR Test

1. Provision clean environment
2. Execute full recovery procedure
3. Verify all functionality
4. Document issues and improvements

## Contact Information

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-call Engineer | TBD | TBD | oncall@acas-pro.com |
| Database Admin | TBD | TBD | dba@acas-pro.com |
| Security Lead | TBD | TBD | security@acas-pro.com |

## External Dependencies

| Service | Provider | Status Page | Escalation |
|---------|----------|-------------|------------|
| Cloud Provider | TBD | TBD | TBD |
| DNS | TBD | TBD | TBD |
| CDN | TBD | TBD | TBD |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2024-01-01 | ACAS Team | Initial version |
