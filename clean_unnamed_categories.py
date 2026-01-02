#!/usr/bin/env python
"""
Script to delete unnamed/empty job categories from the database
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from jobs.models import JobCategory
from django.db.models import Q

# Find unnamed categories
unnamed = JobCategory.objects.filter(
    Q(name__isnull=True) | Q(name='') | Q(name__iexact='unnamed category')
)

count = unnamed.count()
print(f"Found {count} unnamed categories")

if count > 0:
    print("Deleting unnamed categories...")
    unnamed.delete()
    print(f"✓ Deleted {count} unnamed categories")
else:
    print("✓ No unnamed categories found")

# Show remaining categories
remaining = JobCategory.objects.count()
print(f"\nTotal categories remaining: {remaining}")
