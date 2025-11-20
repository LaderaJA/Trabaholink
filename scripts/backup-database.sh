#!/bin/bash
# Database backup script for Trabaholink
# Creates timestamped PostgreSQL backups

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="trabaholink_backup_$TIMESTAMP.sql"

echo "🗄️  Trabaholink Database Backup"
echo "=============================="
echo ""

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if Docker container is running
if ! docker-compose ps | grep -q "trabaholink_db.*Up"; then
    echo "❌ Database container is not running!"
    echo "   Start it with: docker-compose up -d db"
    exit 1
fi

echo "📦 Creating backup: $BACKUP_FILE"
echo ""

# Create backup
docker-compose exec -T db pg_dump -U postgres trabaholink > "$BACKUP_DIR/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    # Compress backup
    gzip "$BACKUP_DIR/$BACKUP_FILE"
    
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE.gz" | cut -f1)
    
    echo "✅ Backup completed successfully!"
    echo ""
    echo "📁 Backup saved to: $BACKUP_DIR/$BACKUP_FILE.gz"
    echo "📊 Size: $BACKUP_SIZE"
    echo ""
    
    # Keep only last 7 backups
    echo "🧹 Cleaning old backups (keeping last 7)..."
    cd "$BACKUP_DIR"
    ls -t trabaholink_backup_*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm
    
    echo ""
    echo "📋 Available backups:"
    ls -lh trabaholink_backup_*.sql.gz 2>/dev/null || echo "   (none)"
else
    echo "❌ Backup failed!"
    exit 1
fi

echo ""
echo "✅ Done!"
