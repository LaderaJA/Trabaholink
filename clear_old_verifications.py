#!/usr/bin/env python
"""
Clear old pending verifications and show current ones
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from users.models import AccountVerification, CustomUser

print("=" * 80)
print("CLEARING OLD PENDING VERIFICATIONS")
print("=" * 80)

# Get all pending verifications
pending = AccountVerification.objects.filter(status='pending').order_by('-submitted_at')

print(f"\nFound {pending.count()} pending verifications:\n")

for v in pending:
    print(f"ID: {v.id}")
    print(f"User: {v.user.username} ({v.user.first_name} {v.user.last_name})")
    print(f"ID Type: {v.id_type}")
    print(f"DOB: {v.date_of_birth}")
    print(f"Submitted: {v.submitted_at}")
    print(f"Status: {v.status}")
    print("-" * 40)

print("\n" + "=" * 80)
print("WHICH VERIFICATIONS TO KEEP?")
print("=" * 80)

# Show which user is henry
try:
    henry = CustomUser.objects.get(username='henry')
    henry_verifications = pending.filter(user=henry)
    
    if henry_verifications.exists():
        print(f"\n✅ Henry's verifications found:")
        for v in henry_verifications:
            print(f"   - Verification ID {v.id}: {v.id_type}, DOB: {v.date_of_birth}")
    else:
        print(f"\n⚠️ No pending verifications for henry found!")
        print(f"   Henry's current verification status: {henry.identity_verification_status}")
        
        # Check if there are any verifications at all
        all_henry_verifications = AccountVerification.objects.filter(user=henry).order_by('-submitted_at')
        if all_henry_verifications.exists():
            print(f"\n   Henry's recent verifications:")
            for v in all_henry_verifications[:3]:
                print(f"   - ID {v.id}: {v.status}, {v.id_type}, submitted {v.submitted_at}")
        
except CustomUser.DoesNotExist:
    print("\n⚠️ User 'henry' not found!")

print("\n" + "=" * 80)
print("RECOMMENDATION:")
print("=" * 80)
print("1. Delete old rejected/failed verifications")
print("2. Keep only the most recent verification for henry")
print("3. Restart Celery to process clean queue")
print("\nTo manually clear, go to Django admin:")
print("http://127.0.0.1:8000/admin/users/accountverification/")
