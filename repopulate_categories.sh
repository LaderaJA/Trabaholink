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
count = JobCategory.objects.count()
print(f"Current categories in database: {count}")
if count > 0:
    JobCategory.objects.all().delete()
    print("✓ All existing categories deleted")
else:
    print("✓ No existing categories to delete")
PYTHON_EOF

echo ""
echo "Step 2: Populating new job categories..."
$PYTHON_CMD populate_job_categories

echo ""
echo "Step 3: Verification..."
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
