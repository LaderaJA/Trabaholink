#!/bin/bash
# Script to diagnose and fix the HistoricalJob issue

echo "=========================================="
echo "HISTORICAL MODELS FIX - DIAGNOSTIC & REPAIR"
echo "=========================================="

cd /root/Trabaholink || exit 1

echo ""
echo "Step 1: Check current migration status..."
echo "-------------------------------------------"
docker-compose exec web python manage.py showmigrations jobs | tail -10

echo ""
echo "Step 2: Run diagnostic script..."
echo "-------------------------------------------"
docker-compose exec -T web python manage.py shell < tmp_rovodev_diagnose_historical.py

echo ""
echo "Step 3: Check for pending migrations..."
echo "-------------------------------------------"
docker-compose exec web python manage.py showmigrations --plan | grep jobs | tail -5

echo ""
echo "Step 4: Apply migrations..."
echo "-------------------------------------------"
docker-compose exec web python manage.py migrate jobs --verbosity 2

echo ""
echo "Step 5: Verify fix..."
echo "-------------------------------------------"
docker-compose exec -T web python manage.py shell << 'PYTHON'
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_name='jobs_historicaljob' AND (column_name LIKE '%_en' OR column_name LIKE '%_tl');")
    count = cursor.fetchone()[0]
    print(f"\nTranslation fields in HistoricalJob table: {count}")
    if count >= 8:
        print("✓ SUCCESS! Historical models have translation fields")
    else:
        print("❌ FAILED! Fields were not added")
PYTHON

echo ""
echo "=========================================="
echo "Diagnostic complete. Check output above."
echo "=========================================="
