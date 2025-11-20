#!/usr/bin/env python
"""
Manually process pending verification
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from users.models import IdentityVerification
from users.tasks import process_verification

# Get pending verifications
pending = IdentityVerification.objects.filter(status='pending').order_by('-submitted_at')

print(f"Found {pending.count()} pending verifications\n")

for verification in pending:
    print(f"Processing verification for: {verification.user.username}")
    print(f"ID Type: {verification.id_type}")
    print(f"Submitted: {verification.submitted_at}")
    
    try:
        # Call the verification task directly (synchronously)
        result = process_verification(verification.id)
        print(f"✅ Result: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("-" * 50)
