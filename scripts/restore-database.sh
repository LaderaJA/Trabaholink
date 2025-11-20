#!/bin/bash
# Database restore script for Trabaholink
# Restores PostgreSQL database from backup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../backups/postgres"

echo "🔄 Trabaholink Database Restore"
echo "==============================="
echo ""

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# List available backups
echo "📋 Available backups:"
echo ""
BACKUPS=($(ls -t "$BACKUP_DIR"/trabaholink_backup_*.sql.gz 2>/dev/null || true))

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo "❌ No backups found in $BACKUP_DIR"
    exit 1
fi

# Display numbered list
for i in "${!BACKUPS[@]}"; do
    BACKUP_FILE=$(basename "${BACKUPS[$i]}")
    BACKUP_SIZE=$(du -h "${BACKUPS[$i]}" | cut -f1)
    echo "[$i] $BACKUP_FILE ($BACKUP_SIZE)"
done

echo ""
read -p "Enter backup number to restore (or 'q' to quit): " SELECTION

if [ "$SELECTION" = "q" ]; then
    echo "Aborted."
    exit 0
fi

# Validate selection
if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -ge "${#BACKUPS[@]}" ]; then
    echo "❌ Invalid selection!"
    exit 1
fi

SELECTED_BACKUP="${BACKUPS[$SELECTION]}"
BACKUP_NAME=$(basename "$SELECTED_BACKUP")

echo ""
echo "⚠️  WARNING: This will overwrite the current database!"
echo "Selected backup: $BACKUP_NAME"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Check if Docker container is running
if ! docker-compose ps | grep -q "trabaholink_db.*Up"; then
    echo "❌ Database container is not running!"
    echo "   Start it with: docker-compose up -d db"
    exit 1
fi

echo ""
echo "🔄 Restoring database from: $BACKUP_NAME"
echo ""

# Decompress backup to temp file
TEMP_BACKUP="/tmp/trabaholink_restore_temp.sql"
gunzip -c "$SELECTED_BACKUP" > "$TEMP_BACKUP"

# Drop existing database and recreate
echo "📝 Dropping existing database..."
docker-compose exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS trabaholink;"
docker-compose exec -T db psql -U postgres -c "CREATE DATABASE trabaholink;"

# Restore backup
echo "📥 Restoring data..."
docker-compose exec -T db psql -U postgres trabaholink < "$TEMP_BACKUP"

# Clean up temp file
rm "$TEMP_BACKUP"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored successfully!"
    echo ""
    echo "🔄 Restarting services..."
    docker-compose restart web celery_worker celery_beat
    
    echo ""
    echo "✅ Done! Your database has been restored from: $BACKUP_NAME"
else
    echo "❌ Restore failed!"
    exit 1
fi
