#!/bin/sh

# NGX Voice Sales Agent - Database Backup Script
# Runs daily to backup PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backups"
DB_HOST="${DB_HOST:-postgres}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-ngx_voice_agent}"
DB_USER="${DB_USER:-postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/ngx_backup_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting database backup..."

# Perform backup
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose --no-owner --no-acl --clean --if-exists \
    | gzip > "$BACKUP_FILE"

# Check if backup was successful
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup completed successfully: $BACKUP_FILE (Size: $SIZE)"
    
    # Cleanup old backups
    echo "[$(date)] Cleaning up backups older than $RETENTION_DAYS days..."
    find "$BACKUP_DIR" -name "ngx_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    
    # List current backups
    echo "[$(date)] Current backups:"
    ls -lh "$BACKUP_DIR"/ngx_backup_*.sql.gz 2>/dev/null || echo "No backups found"
else
    echo "[$(date)] ERROR: Backup failed!"
    exit 1
fi

echo "[$(date)] Backup process completed"