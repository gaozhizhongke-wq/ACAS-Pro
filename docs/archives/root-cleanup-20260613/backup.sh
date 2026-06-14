#!/usr/bin/env bash
# ACAS Pro - 数据库备份脚本
# 用途: 备份 PostgreSQL 数据库到本地文件
# 用法: ./backup.sh [保留天数]
# 默认保留 7 天

set -euo pipefail

# ============================================
# 配置
# ============================================
# 备份目录（修改为实际路径）
BACKUP_DIR="${BACKUP_DIR:-./backups}"
# 保留天数
KEEP_DAYS="${KEEP_DAYS:-7}"
# 当前日期
DATE=$(date +%Y%m%d_%H%M%S)
TIMESTAMP=$(date +%Y%m%d)
# 数据库配置
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-acas_pro}"
DB_USER="${DB_USER:-acas_user}"
# 压缩格式 (gz 或 bz2)
COMPRESS="${COMPRESS:-gz}"

# ============================================
# 初始化
# ============================================
mkdir -p "$BACKUP_DIR"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === ACAS Pro 数据库备份 ==="

# ============================================
# 备份函数
# ============================================
do_backup() {
    local backup_file="$1"
    local start_time=$SECONDS

    echo "开始备份: $DB_NAME -> $backup_file"

    # 使用 pg_dump 备份
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --no-owner \
        --no-acl \
        -Fc \
        -f "$backup_file"

    local duration=$(( SECONDS - start_time ))
    local size=$(du -h "$backup_file" | cut -f1)
    echo "✅ 备份完成: $backup_file ($size, ${duration}s)"
}

# ============================================
# 清理旧备份
# ============================================
cleanup_old() {
    echo "清理超过 $KEEP_DAYS 天的备份..."

    # 删除 TIMESTAMP 日期前的备份
    find "$BACKUP_DIR" -name "acas_*.sqlc" -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true

    # 统计剩余备份数
    local remaining=$(find "$BACKUP_DIR" -name "acas_*.sqlc" | wc -l)
    echo "清理完成，剩余 $remaining 个备份"
}

# ============================================
# 主流程
# ============================================
# 生成备份文件名
BACKUP_FILE="$BACKUP_DIR/acas_${DATE}.sqlc"

# 执行备份
do_backup "$BACKUP_FILE"

# 清理旧备份
cleanup_old

# 生成校验和
if command -v sha256sum > /dev/null 2>&1; then
    sha256sum "$BACKUP_FILE" > "${BACKUP_FILE}.sha256"
    echo "校验和: ${BACKUP_FILE}.sha256"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 备份完成 ==="