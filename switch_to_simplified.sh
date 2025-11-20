#!/bin/bash

# Script to switch to simplified verification system

echo "🔄 Switching to Simplified Verification System..."
echo ""

# Backup current files
echo "1️⃣ Creating backups..."
cp templates/admin_dashboard/user_verification_detail.html templates/admin_dashboard/user_verification_detail_backup_$(date +%Y%m%d_%H%M%S).html
echo "✅ Backed up template"

# Replace with simplified template
echo ""
echo "2️⃣ Installing simplified template..."
cp templates/admin_dashboard/user_verification_detail_simple.html templates/admin_dashboard/user_verification_detail.html
echo "✅ Simplified template installed"

# Create a simple URL update script
echo ""
echo "3️⃣ Creating URL configuration..."
cat > admin_dashboard/urls_simplified_addition.py << 'EOF'
# Add these imports to admin_dashboard/urls.py
from admin_dashboard import views_simple

# Replace these URL patterns:
# path('identity-verifications/<int:pk>/', views.UserVerificationDetailView.as_view(), name='user_verification_detail'),
# path('identity-verifications/<int:pk>/approve/', views.approve_identity_verification, name='approve_identity_verification'),
# path('identity-verifications/<int:pk>/reject/', views.reject_identity_verification, name='reject_identity_verification'),
# path('identity-verifications/<int:pk>/reprocess/', views.reprocess_verification, name='reprocess_verification'),

# With these:
path('identity-verifications/<int:pk>/', views_simple.UserVerificationDetailSimpleView.as_view(), name='user_verification_detail'),
path('identity-verifications/<int:pk>/approve/', views_simple.approve_verification_simple, name='approve_identity_verification'),
path('identity-verifications/<int:pk>/reject/', views_simple.reject_verification_simple, name='reject_identity_verification'),
path('identity-verifications/<int:pk>/reprocess/', views_simple.reprocess_ocr_simple, name='reprocess_verification'),
EOF

echo "✅ URL configuration guide created: admin_dashboard/urls_simplified_addition.py"

echo ""
echo "4️⃣ Next steps:"
echo ""
echo "   Manual step required:"
echo "   Edit admin_dashboard/urls.py and update the URL patterns"
echo "   See: admin_dashboard/urls_simplified_addition.py for the changes"
echo ""
echo "   Then restart services:"
echo "   ./restart_services.sh"
echo "   python3 manage.py runserver"
echo ""
echo "✅ Simplified system files are ready!"
echo ""
echo "📖 See SIMPLIFIED_VERIFICATION_GUIDE.md for complete documentation"
