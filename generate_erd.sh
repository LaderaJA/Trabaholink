#!/bin/bash

# ========================================
# Trabaholink ERD Generator Script
# ========================================
# This script generates an Entity Relationship Diagram (ERD) from Django models
# and automatically downloads it to your local machine

set -e  # Exit on error

echo "=========================================="
echo "Trabaholink ERD Generator"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running on production or local
if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓ Found docker-compose.yml${NC}"
    DOCKER_CMD="docker-compose"
else
    echo -e "${RED}✗ docker-compose.yml not found${NC}"
    exit 1
fi

# Step 1: Install required packages
echo ""
echo "Step 1: Installing required packages..."
$DOCKER_CMD exec web pip install django-extensions pydotplus -q
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Packages installed${NC}"
else
    echo -e "${RED}✗ Failed to install packages${NC}"
    exit 1
fi

# Step 2: Add django_extensions to INSTALLED_APPS if not already added
echo ""
echo "Step 2: Checking django_extensions in settings..."
$DOCKER_CMD exec web python manage.py shell << 'PYEOF'
from django.conf import settings
if 'django_extensions' not in settings.INSTALLED_APPS:
    print("WARNING: 'django_extensions' not in INSTALLED_APPS")
    print("Please add it to Trabaholink/settings.py manually")
else:
    print("✓ django_extensions is configured")
PYEOF

# Step 3: Generate ERD diagrams
echo ""
echo "Step 3: Generating ERD diagrams..."

# Generate full ERD with all apps
echo "  → Generating full ERD (all apps)..."
$DOCKER_CMD exec web python manage.py graph_models -a -g -o /app/erd_full.png
if [ $? -eq 0 ]; then
    echo -e "    ${GREEN}✓ Full ERD generated${NC}"
else
    echo -e "    ${YELLOW}⚠ Full ERD generation failed (continuing...)${NC}"
fi

# Generate main apps ERD
echo "  → Generating main apps ERD..."
$DOCKER_CMD exec web python manage.py graph_models users jobs messaging announcements services notifications -g -o /app/erd_main.png
if [ $? -eq 0 ]; then
    echo -e "    ${GREEN}✓ Main apps ERD generated${NC}"
else
    echo -e "    ${YELLOW}⚠ Main apps ERD generation failed (continuing...)${NC}"
fi

# Generate grouped ERD
echo "  → Generating grouped ERD..."
$DOCKER_CMD exec web python manage.py graph_models -a --group-models -o /app/erd_grouped.png
if [ $? -eq 0 ]; then
    echo -e "    ${GREEN}✓ Grouped ERD generated${NC}"
else
    echo -e "    ${YELLOW}⚠ Grouped ERD generation failed (continuing...)${NC}"
fi

# Generate SVG format (scalable)
echo "  → Generating SVG ERD..."
$DOCKER_CMD exec web python manage.py graph_models -a -g -o /app/erd_full.svg
if [ $? -eq 0 ]; then
    echo -e "    ${GREEN}✓ SVG ERD generated${NC}"
else
    echo -e "    ${YELLOW}⚠ SVG ERD generation failed (continuing...)${NC}"
fi

# Step 4: Copy files from container to host
echo ""
echo "Step 4: Copying ERD files from container..."

# Get container name
CONTAINER_NAME=$($DOCKER_CMD ps --format "{{.Names}}" | grep web | head -1)

if [ -z "$CONTAINER_NAME" ]; then
    echo -e "${RED}✗ Could not find web container${NC}"
    exit 1
fi

echo "  → Using container: $CONTAINER_NAME"

# Create ERD directory
mkdir -p ./erd_output
echo -e "  ${GREEN}✓ Created ./erd_output directory${NC}"

# Copy files
echo "  → Copying files..."
docker cp ${CONTAINER_NAME}:/app/erd_full.png ./erd_output/erd_full.png 2>/dev/null && echo -e "    ${GREEN}✓ erd_full.png${NC}" || echo -e "    ${YELLOW}⚠ erd_full.png not found${NC}"
docker cp ${CONTAINER_NAME}:/app/erd_main.png ./erd_output/erd_main.png 2>/dev/null && echo -e "    ${GREEN}✓ erd_main.png${NC}" || echo -e "    ${YELLOW}⚠ erd_main.png not found${NC}"
docker cp ${CONTAINER_NAME}:/app/erd_grouped.png ./erd_output/erd_grouped.png 2>/dev/null && echo -e "    ${GREEN}✓ erd_grouped.png${NC}" || echo -e "    ${YELLOW}⚠ erd_grouped.png not found${NC}"
docker cp ${CONTAINER_NAME}:/app/erd_full.svg ./erd_output/erd_full.svg 2>/dev/null && echo -e "    ${GREEN}✓ erd_full.svg${NC}" || echo -e "    ${YELLOW}⚠ erd_full.svg not found${NC}"

# Step 5: Generate README
echo ""
echo "Step 5: Creating README..."
cat > ./erd_output/README.md << 'EOF'
# Trabaholink ERD (Entity Relationship Diagram)

Generated on: $(date)

## Files

- **erd_full.png** - Complete ERD with all Django apps and models
- **erd_main.png** - Main business logic apps (users, jobs, messaging, etc.)
- **erd_grouped.png** - ERD with models grouped by app
- **erd_full.svg** - Scalable vector format (best for zooming)

## How to View

### PNG/SVG Files
- Open with any image viewer
- Recommended: Use a browser or image editor that supports zooming

### Best Practices
- Use **erd_main.png** for overview of core functionality
- Use **erd_full.png** for complete database structure
- Use **erd_grouped.png** to understand app organization
- Use **erd_full.svg** for presentations (scalable)

## Model Relationships

### Core Models
- **CustomUser** - Central user model
- **Job** - Job postings with location data
- **JobApplication** - Worker applications
- **Contract** - Employment contracts
- **Conversation** - Messaging system
- **Announcement** - System announcements
- **Service** - Marketplace services

### Key Relationships
- User → Job (1:many) - posted_jobs
- User → JobApplication (1:many) - job_applications
- Job → JobApplication (1:many) - applications
- JobApplication → Contract (1:1) - contract
- User → Conversation (many:many) - participants
- Conversation → Message (1:many) - messages

## Apps Included

1. **users** - Authentication, profiles, skills, education
2. **jobs** - Job postings, applications, contracts
3. **messaging** - Conversations and messages
4. **announcements** - System announcements
5. **services** - Service marketplace
6. **notifications** - User notifications
7. **admin_dashboard** - Admin management
8. **reports** - Reporting system

## Regenerate ERD

To regenerate the ERD:
```bash
./generate_erd.sh
```

## Notes

- Some Django internal tables (e.g., migrations, sessions) may be excluded
- The diagram shows ForeignKey, OneToOne, and ManyToMany relationships
- Generated using django-extensions graph_models command
EOF

echo -e "${GREEN}✓ README created${NC}"

# Step 6: Generate text summary
echo ""
echo "Step 6: Generating model summary..."
$DOCKER_CMD exec web python manage.py shell << 'PYEOF' > ./erd_output/models_summary.txt
from django.apps import apps

print("=" * 80)
print("TRABAHOLINK DATABASE MODELS SUMMARY")
print("=" * 80)
print()

# Group models by app
app_models = {}
for model in apps.get_models():
    app_label = model._meta.app_label
    if app_label not in app_models:
        app_models[app_label] = []
    app_models[app_label].append(model)

# Print each app
for app_label in sorted(app_models.keys()):
    print(f"\n{'=' * 80}")
    print(f"APP: {app_label.upper()}")
    print(f"{'=' * 80}")
    
    for model in sorted(app_models[app_label], key=lambda x: x.__name__):
        print(f"\n{model.__name__}")
        print(f"  Table: {model._meta.db_table}")
        print(f"  Fields: {len(model._meta.fields)}")
        
        # List fields
        for field in model._meta.fields:
            field_type = field.get_internal_type()
            null_str = "NULL" if field.null else "NOT NULL"
            pk_str = "PK" if field.primary_key else ""
            print(f"    - {field.name:30} {field_type:20} {null_str:10} {pk_str}")
        
        # List relationships
        relations = []
        for field in model._meta.fields:
            if field.get_internal_type() in ['ForeignKey', 'OneToOneField']:
                related = field.related_model._meta.label
                relations.append(f"{field.name} → {related}")
        
        if relations:
            print(f"  Relationships:")
            for rel in relations:
                print(f"    - {rel}")

print("\n" + "=" * 80)
print(f"TOTAL MODELS: {len(apps.get_models())}")
print("=" * 80)
PYEOF

echo -e "${GREEN}✓ Model summary created${NC}"

# Step 7: Cleanup container files
echo ""
echo "Step 7: Cleaning up container files..."
$DOCKER_CMD exec web rm -f /app/erd_*.png /app/erd_*.svg 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"

# Final summary
echo ""
echo "=========================================="
echo -e "${GREEN}✓ ERD Generation Complete!${NC}"
echo "=========================================="
echo ""
echo "Files saved to: ./erd_output/"
echo ""
ls -lh ./erd_output/ | tail -n +2 | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "View the ERD:"
echo "  1. Open ./erd_output/erd_main.png for overview"
echo "  2. Open ./erd_output/erd_full.png for complete diagram"
echo "  3. Read ./erd_output/README.md for details"
echo "  4. Check ./erd_output/models_summary.txt for text summary"
echo ""
echo -e "${GREEN}Done!${NC}"
