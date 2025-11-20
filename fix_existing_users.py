#!/usr/bin/env python
"""
Script to fix existing users by setting role_selected=True
Run this once to update all existing users who already have roles.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from users.models import CustomUser

print("🔍 Finding users with role_selected=False...")

# Get all users where role_selected is False
users = CustomUser.objects.filter(role_selected=False)
print(f"Found {users.count()} users with role_selected=False\n")

count = 0
for user in users:
    if user.role:  # If user has a role
        user.role_selected = True
        user.save(update_fields=['role_selected'])
        count += 1
        print(f'✅ Updated: {user.username} (role: {user.role})')

print(f'\n✅ Successfully updated {count} users!')
print("All existing users now have role_selected=True")
