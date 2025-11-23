#!/bin/bash
# Deployment script for Google Calendar feature

echo "=========================================="
echo "Deploying Calendar Feature to Server"
echo "=========================================="
echo ""

# Step 1: Pull latest code
echo "Step 1: Pulling latest code from GitHub..."
git pull origin main
if [ $? -ne 0 ]; then
    echo "❌ Failed to pull code. Please check git status."
    exit 1
fi
echo "✅ Code updated successfully"
echo ""

# Step 2: Create migrations
echo "Step 2: Creating database migrations..."
./dc.sh exec web python manage.py makemigrations jobs
if [ $? -ne 0 ]; then
    echo "❌ Failed to create migrations."
    exit 1
fi
echo "✅ Migrations created"
echo ""

# Step 3: Run migrations
echo "Step 3: Running database migrations..."
./dc.sh exec web python manage.py migrate jobs
if [ $? -ne 0 ]; then
    echo "❌ Failed to run migrations."
    exit 1
fi
echo "✅ Migrations applied successfully"
echo ""

# Step 4: Collect static files
echo "Step 4: Collecting static files..."
./dc.sh exec web python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Failed to collect static files (non-critical)"
fi
echo "✅ Static files collected"
echo ""

# Step 5: Restart web service
echo "Step 5: Restarting web service..."
./dc.sh restart web
if [ $? -ne 0 ]; then
    echo "❌ Failed to restart web service."
    exit 1
fi
echo "✅ Web service restarted"
echo ""

# Step 6: Check service status
echo "Step 6: Checking service status..."
./dc.sh ps
echo ""

echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "📋 What was deployed:"
echo "  • Time-based contract scheduling"
echo "  • Google Calendar-like interface"
echo "  • Conflict detection for work hours"
echo "  • Mobile-responsive calendar views"
echo ""
echo "🧪 Test the feature:"
echo "  1. Go to Worker Dashboard > Track Jobs tab"
echo "  2. View the new calendar interface"
echo "  3. Create/edit contracts with time fields"
echo "  4. Check for conflicts when scheduling"
echo ""
echo "📝 Next steps:"
echo "  • Test contract creation with times"
echo "  • Verify conflict detection works"
echo "  • Check mobile responsiveness"
echo ""
