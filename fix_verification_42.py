#!/usr/bin/env python
"""Fix verification 42 that was auto-approved but reverted to pending"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from users.models import AccountVerification, VerificationLog
from django.utils import timezone

v = AccountVerification.objects.get(id=42)
logs = VerificationLog.objects.filter(user=v.user).order_by('-created_at').first()

if logs and 'Auto-approved' in (logs.notes or ''):
    print('Found auto-approval in logs')
    v.status = 'approved'
    v.reviewed_at = timezone.now()
    v.save()
    
    v.user.verification_status = 'verified'
    v.user.identity_verification_status = 'verified'
    v.user.is_verified = True
    v.user.save()
    
    print(f'Fixed verification {v.id}')
    print(f'  Status: {v.status}')
    print(f'  User verification_status: {v.user.verification_status}')
else:
    print('No auto-approval found')
    if logs:
        print(f'Latest log notes: {logs.notes[:200]}')
