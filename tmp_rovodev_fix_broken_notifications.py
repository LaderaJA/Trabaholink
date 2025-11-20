#!/usr/bin/env python
"""
Script to identify and fix broken notification links
Run this script to clean up notifications with deleted object references
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta


def main():
    print("=" * 70)
    print("NOTIFICATION CLEANUP UTILITY")
    print("=" * 70)
    print()
    
    # Get all notifications with object references
    all_notifications = Notification.objects.filter(object_id__isnull=False)
    total_count = all_notifications.count()
    
    print(f"📊 Total notifications with object references: {total_count}")
    print()
    
    # Check for broken references
    broken_notifications = []
    
    print("🔍 Scanning for broken references...")
    for notification in all_notifications:
        if notification.is_object_deleted:
            broken_notifications.append(notification)
    
    broken_count = len(broken_notifications)
    print(f"❌ Found {broken_count} notifications with broken references")
    print()
    
    if broken_count == 0:
        print("✅ No broken notifications found! All notification links are valid.")
        return
    
    # Show breakdown by type
    print("📋 Breakdown by notification type:")
    type_counts = {}
    for notif in broken_notifications:
        notif_type = notif.notif_type
        type_counts[notif_type] = type_counts.get(notif_type, 0) + 1
    
    for notif_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {notif_type}: {count}")
    print()
    
    # Show breakdown by age
    now = timezone.now()
    age_ranges = {
        '< 7 days': 0,
        '7-30 days': 0,
        '30-90 days': 0,
        '> 90 days': 0
    }
    
    for notif in broken_notifications:
        age = (now - notif.created_at).days
        if age < 7:
            age_ranges['< 7 days'] += 1
        elif age < 30:
            age_ranges['7-30 days'] += 1
        elif age < 90:
            age_ranges['30-90 days'] += 1
        else:
            age_ranges['> 90 days'] += 1
    
    print("📅 Age distribution of broken notifications:")
    for age_range, count in age_ranges.items():
        print(f"  • {age_range}: {count}")
    print()
    
    # Ask user what to do
    print("=" * 70)
    print("CLEANUP OPTIONS:")
    print("=" * 70)
    print("1. Archive all broken notifications")
    print("2. Archive broken notifications older than 30 days")
    print("3. Delete all broken notifications")
    print("4. Delete broken notifications older than 30 days")
    print("5. Show detailed list (first 10)")
    print("6. Exit without changes")
    print()
    
    choice = input("Enter your choice (1-6): ").strip()
    
    if choice == '1':
        confirm = input(f"Archive all {broken_count} broken notifications? (yes/no): ").strip().lower()
        if confirm == 'yes':
            for notif in broken_notifications:
                notif.archive()
            print(f"✅ Archived {broken_count} notifications")
    
    elif choice == '2':
        cutoff = timezone.now() - timedelta(days=30)
        old_broken = [n for n in broken_notifications if n.created_at < cutoff]
        count = len(old_broken)
        confirm = input(f"Archive {count} broken notifications older than 30 days? (yes/no): ").strip().lower()
        if confirm == 'yes':
            for notif in old_broken:
                notif.archive()
            print(f"✅ Archived {count} notifications")
    
    elif choice == '3':
        confirm = input(f"⚠️  DELETE all {broken_count} broken notifications? This cannot be undone! (yes/no): ").strip().lower()
        if confirm == 'yes':
            confirm2 = input("Are you absolutely sure? Type 'DELETE' to confirm: ").strip()
            if confirm2 == 'DELETE':
                for notif in broken_notifications:
                    notif.delete()
                print(f"✅ Deleted {broken_count} notifications")
            else:
                print("❌ Deletion cancelled")
    
    elif choice == '4':
        cutoff = timezone.now() - timedelta(days=30)
        old_broken = [n for n in broken_notifications if n.created_at < cutoff]
        count = len(old_broken)
        confirm = input(f"⚠️  DELETE {count} broken notifications older than 30 days? This cannot be undone! (yes/no): ").strip().lower()
        if confirm == 'yes':
            confirm2 = input("Are you absolutely sure? Type 'DELETE' to confirm: ").strip()
            if confirm2 == 'DELETE':
                for notif in old_broken:
                    notif.delete()
                print(f"✅ Deleted {count} notifications")
            else:
                print("❌ Deletion cancelled")
    
    elif choice == '5':
        print("\n" + "=" * 70)
        print("DETAILED LIST (First 10):")
        print("=" * 70)
        for i, notif in enumerate(broken_notifications[:10], 1):
            age_days = (now - notif.created_at).days
            print(f"\n{i}. ID: {notif.id}")
            print(f"   User: {notif.user.username}")
            print(f"   Type: {notif.notif_type}")
            print(f"   Message: {notif.message[:80]}...")
            print(f"   Age: {age_days} days")
            print(f"   Created: {notif.created_at.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Read: {'Yes' if notif.is_read else 'No'}")
        
        if broken_count > 10:
            print(f"\n... and {broken_count - 10} more")
    
    elif choice == '6':
        print("❌ Exiting without changes")
    
    else:
        print("❌ Invalid choice")
    
    print()
    print("=" * 70)
    print("Done!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
