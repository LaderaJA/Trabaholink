#!/bin/bash
# Script to clear and repopulate JobCategory table
# This is needed after server transfer when database data is lost

echo "========================================"
echo "Job Categories Repopulation Script"
echo "========================================"
echo ""

# Check if running in Docker
if [ -f "dc.sh" ]; then
    echo "Using Docker Compose..."
    PYTHON_CMD="./dc.sh exec web python manage.py"
else
    echo "Using local Python..."
    PYTHON_CMD="python manage.py"
fi

echo ""
echo "Step 1: Clearing existing job categories..."
$PYTHON_CMD shell << PYTHON_EOF
from jobs.models import JobCategory
from django.db import connection, transaction

count = JobCategory.objects.count()
print(f"Current categories in database: {count}")

# Use transaction to ensure atomic operations
with transaction.atomic():
    if count > 0:
        # Delete all categories
        JobCategory.objects.all().delete()
        print("✓ All existing categories deleted")
        
        # Reset the auto-increment sequence to avoid conflicts
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval(pg_get_serial_sequence('jobs_jobcategory', 'id'), 1, false);")
        print("✓ Database sequence reset")
        
        # Clear any translation fields if they exist
        with connection.cursor() as cursor:
            # Check if translation columns exist and clear them
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'jobs_jobcategory' 
                AND column_name LIKE 'name_%'
            """)
            trans_cols = cursor.fetchall()
            if trans_cols:
                print(f"✓ Found {len(trans_cols)} translation columns")
    else:
        print("✓ No existing categories to delete")

print("✓ Database is clean and ready")
PYTHON_EOF

echo ""
echo "Step 2: Truncating table and resetting (force clean)..."
$PYTHON_CMD shell << PYTHON_EOF
from django.db import connection
from jobs.models import JobCategory

# Force truncate the table and reset sequence
with connection.cursor() as cursor:
    # Truncate will delete all rows and reset auto-increment
    cursor.execute("TRUNCATE TABLE jobs_jobcategory RESTART IDENTITY CASCADE;")
    print("✓ Table truncated and sequence reset")

# Verify it's empty
count = JobCategory.objects.count()
print(f"✓ Verified: {count} categories in database (should be 0)")
PYTHON_EOF

echo ""
echo "Step 3: Populating new job categories..."
$PYTHON_CMD populate_job_categories

echo ""
echo "Step 4: Verification..."
$PYTHON_CMD shell << PYTHON_EOF
from jobs.models import JobCategory
count = JobCategory.objects.count()
print(f"Total categories in database: {count}")
print("")
print("Sample categories:")
for cat in JobCategory.objects.all()[:10]:
    print(f"  - {cat.name}")
if count > 10:
    print(f"  ... and {count - 10} more")
PYTHON_EOF

echo ""
echo "========================================"
echo "✓ Job categories repopulation complete!"
echo "========================================"
