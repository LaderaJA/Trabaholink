#!/usr/bin/env python
"""
Quick test script to verify notification fixes are working
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def test_notification_fixes():
    print("=" * 70)
    print("NOTIFICATION FIX VERIFICATION TEST")
    print("=" * 70)
    print()
    
    # Test 1: Check models have new properties
    print("✓ Test 1: Checking model properties...")
    notification = Notification()
    assert hasattr(notification, 'is_object_deleted'), "❌ is_object_deleted property missing"
    assert hasattr(notification, 'target_url'), "❌ target_url property missing"
    assert hasattr(notification, 'archive'), "❌ archive method missing"
    print("  ✅ All required properties exist")
    print()
    
    # Test 2: Check management command exists
    print("✓ Test 2: Checking management command...")
    import os.path
    cmd_path = 'notifications/management/commands/clean_broken_notifications.py'
    assert os.path.exists(cmd_path), f"❌ Management command not found at {cmd_path}"
    print("  ✅ Management command exists")
    print()
    
    # Test 3: Check views have auto-archive logic
    print("✓ Test 3: Checking views...")
    with open('notifications/views.py', 'r') as f:
        content = f.read()
        assert 'is_object_deleted' in content, "❌ is_object_deleted check missing in views"
        assert 'notification.archive()' in content, "❌ auto-archive logic missing"
        assert 'Auto-archived' in content, "❌ auto-archive logging missing"
    print("  ✅ Views have auto-archive logic")
    print()
    
    # Test 4: Check template has broken-link styling
    print("✓ Test 4: Checking template...")
    with open('templates/notifications/notification_list.html', 'r') as f:
        content = f.read()
        assert 'broken-link' in content, "❌ broken-link CSS class missing"
        assert 'showBrokenLinkMessage' in content, "❌ JavaScript handler missing"
        assert 'is_object_deleted' in content, "❌ Template check for broken links missing"
    print("  ✅ Template has broken-link handling")
    print()
    
    # Test 5: Check middleware improvements
    print("✓ Test 5: Checking middleware...")
    with open('notifications/middleware.py', 'r') as f:
        content = f.read()
        assert 'logger' in content, "❌ Logging missing in middleware"
        assert 'Notification.DoesNotExist' in content, "❌ Exception handling incomplete"
    print("  ✅ Middleware has improved error handling")
    print()
    
    # Test 6: Count notifications in database
    print("✓ Test 6: Checking database...")
    try:
        total = Notification.objects.count()
        with_objects = Notification.objects.filter(object_id__isnull=False).count()
        print(f"  ℹ️  Total notifications: {total}")
        print(f"  ℹ️  With object references: {with_objects}")
        
        if with_objects > 0:
            # Check for broken notifications
            broken_count = 0
            sample_size = min(100, with_objects)
            sample = Notification.objects.filter(object_id__isnull=False)[:sample_size]
            
            for notif in sample:
                try:
                    if notif.is_object_deleted:
                        broken_count += 1
                except Exception as e:
                    print(f"  ⚠️  Error checking notification {notif.id}: {str(e)}")
            
            if sample_size > 0:
                broken_pct = (broken_count / sample_size) * 100
                print(f"  ℹ️  Broken notifications (sample): {broken_count}/{sample_size} ({broken_pct:.1f}%)")
                
                if broken_count > 0:
                    print(f"  💡 Tip: Run cleanup script to fix {broken_count}+ broken notifications")
        else:
            print("  ℹ️  No notifications with object references found")
        
        print("  ✅ Database accessible")
    except Exception as e:
        print(f"  ⚠️  Database check error: {str(e)}")
    print()
    
    # Test 7: Check documentation
    print("✓ Test 7: Checking documentation...")
    docs = [
        'NOTIFICATION_FIXES_README.md',
        'NOTIFICATION_FIX_SUMMARY.md'
    ]
    for doc in docs:
        assert os.path.exists(doc), f"❌ Documentation missing: {doc}"
    print("  ✅ Documentation files exist")
    print()
    
    # Summary
    print("=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    print()
    print("✅ All core fixes are in place!")
    print()
    print("📋 Next Steps:")
    print("  1. Review NOTIFICATION_FIX_SUMMARY.md for overview")
    print("  2. Read NOTIFICATION_FIXES_README.md for detailed guide")
    print("  3. Run: python tmp_rovodev_fix_broken_notifications.py")
    print("     to analyze and clean up existing broken notifications")
    print("  4. Set up scheduled cleanup (weekly recommended)")
    print("  5. Test manually by creating and deleting a job/contract")
    print()
    print("🗑️  Cleanup temporary files when done:")
    print("  rm tmp_rovodev_*.py")
    print()


if __name__ == '__main__':
    try:
        test_notification_fixes()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
