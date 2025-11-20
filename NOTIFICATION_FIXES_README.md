# Notification System Fixes - Documentation

## Overview
This document describes the fixes implemented for notification handling and old broken links in the Trabaholink application.

## Issues Fixed

### 1. **Broken Link Handling**
**Problem:** Notifications referencing deleted objects (jobs, contracts, applications, etc.) would cause errors or lead to 404 pages.

**Solution:**
- Added `is_object_deleted` property to check if referenced objects still exist
- Modified `target_url` property to return `None` for broken links instead of causing errors
- Updated views to auto-archive notifications with broken links
- Added visual indicators in the UI for broken notifications

### 2. **Notification Redirect Issues**
**Problem:** Clicking on notifications with deleted objects would result in errors or poor user experience.

**Solution:**
- Enhanced `NotificationListView.get()` to detect broken links before redirecting
- Auto-archive broken notifications when accessed
- Show user-friendly messages explaining content is no longer available
- Prevent redirect for broken notifications

### 3. **API Error Handling**
**Problem:** API endpoints would fail when processing notifications with broken links.

**Solution:**
- Updated `RecentNotificationsAPIView` to handle broken links gracefully
- Added `is_broken` flag to API responses
- Fallback URLs for broken notifications

### 4. **Middleware Improvements**
**Problem:** Middleware could fail silently or cause issues with invalid notification IDs.

**Solution:**
- Added comprehensive error logging
- Better exception handling for edge cases
- Removed use of `get_object_or_404` in favor of explicit exception handling

## New Features

### 1. **Management Command: `clean_broken_notifications`**
Automatically clean up notifications with broken references.

**Usage:**
```bash
# Dry run - see what would be done
python manage.py clean_broken_notifications --dry-run

# Archive broken notifications older than 30 days (default)
python manage.py clean_broken_notifications

# Archive broken notifications older than 60 days
python manage.py clean_broken_notifications --days=60

# Delete instead of archive
python manage.py clean_broken_notifications --delete

# Dry run with deletion mode
python manage.py clean_broken_notifications --delete --dry-run
```

**Options:**
- `--days`: Age threshold in days (default: 30)
- `--delete`: Delete instead of archiving
- `--dry-run`: Show what would be done without making changes

### 2. **Interactive Cleanup Script**
Run the interactive script to analyze and fix broken notifications:

```bash
python tmp_rovodev_fix_broken_notifications.py
```

**Features:**
- Scans all notifications for broken references
- Shows detailed statistics and breakdown
- Interactive menu to:
  - Archive all broken notifications
  - Archive broken notifications older than 30 days
  - Delete all broken notifications
  - Delete broken notifications older than 30 days
  - View detailed list
  - Exit without changes

### 3. **Auto-Archive Feature**
- Notifications with broken links are automatically archived when accessed
- 30+ day old notifications are auto-archived on notification list view
- Reduces clutter and improves performance

### 4. **Enhanced UI**
- Broken notifications are visually marked with red indicator
- Warning icon and message displayed for unavailable content
- Click on broken notification prompts to archive it
- Non-clickable cursor for broken links

## Technical Changes

### Files Modified

1. **`notifications/models.py`**
   - Modified `target_url` property to return `None` for broken links
   - Enhanced `is_object_deleted` property with better error handling
   - Improved logging throughout

2. **`notifications/views.py`**
   - Enhanced `NotificationListView.get()` with broken link detection
   - Auto-archive functionality for broken notifications
   - Improved error messages for users
   - Updated `RecentNotificationsAPIView` with fallback URLs

3. **`notifications/middleware.py`**
   - Better error handling and logging
   - Removed dependency on `get_object_or_404`
   - More robust validation

4. **`templates/notifications/notification_list.html`**
   - Added `broken-link` CSS class styling
   - Visual indicators for broken notifications
   - JavaScript function to handle broken link clicks
   - Improved user experience

### Files Created

1. **`notifications/management/commands/clean_broken_notifications.py`**
   - Django management command for cleanup

2. **`tmp_rovodev_fix_broken_notifications.py`**
   - Interactive cleanup script (temporary file)

## Usage Examples

### For Administrators

**1. Regular Maintenance (Recommended)**
Schedule this to run weekly:
```bash
python manage.py clean_broken_notifications --days=30
```

**2. Deep Clean**
For major cleanup:
```bash
python manage.py clean_broken_notifications --days=7 --delete
```

**3. Investigation**
To see what would be cleaned:
```bash
python manage.py clean_broken_notifications --dry-run
```

### For Users

**1. Viewing Notifications**
- Broken notifications are clearly marked with red indicator
- Warning message shows "(Content no longer available)"
- Clicking prompts to archive the notification

**2. Cleaning Up**
- Use "Archive Read" button to clean up read notifications
- Broken notifications are automatically archived when accessed

## Best Practices

1. **Regular Cleanup**
   - Run cleanup command weekly or monthly
   - Archive notifications older than 30 days with broken links
   - Consider deleting very old broken notifications (90+ days)

2. **Monitoring**
   - Check Django logs for notification-related warnings
   - Monitor the count of broken notifications
   - Track user reports of notification issues

3. **Prevention**
   - Consider soft-delete pattern for critical models
   - Add database constraints where appropriate
   - Log when objects are deleted that have notifications

## Scheduled Tasks Setup

### Using Cron (Linux/Mac)
Add to crontab (`crontab -e`):
```bash
# Run weekly cleanup on Sunday at 2 AM
0 2 * * 0 cd /path/to/Trabaholink && python manage.py clean_broken_notifications
```

### Using Django-Crontab
In `settings.py`:
```python
CRONJOBS = [
    ('0 2 * * 0', 'django.core.management.call_command', ['clean_broken_notifications']),
]
```

### Using Celery Beat
```python
# In celery.py or tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def clean_broken_notifications_task():
    call_command('clean_broken_notifications', days=30)

# In celery beat schedule
from celery.schedules import crontab

app.conf.beat_schedule = {
    'clean-broken-notifications': {
        'task': 'notifications.tasks.clean_broken_notifications_task',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2 AM
    },
}
```

## Testing

### Manual Testing
1. Create a notification for a job/contract
2. Delete the job/contract
3. View notifications page - should see red indicator
4. Click the broken notification - should prompt to archive
5. Verify auto-archive works

### Automated Testing
```python
# In notifications/tests.py
from django.test import TestCase
from notifications.models import Notification
from jobs.models import Job

class BrokenNotificationTest(TestCase):
    def test_broken_link_detection(self):
        job = Job.objects.create(...)
        notification = Notification.objects.create(
            user=user,
            message="New job",
            notif_type="job_post",
            object_id=job.id
        )
        
        # Delete the job
        job.delete()
        
        # Check notification detects broken link
        self.assertTrue(notification.is_object_deleted)
        self.assertIsNone(notification.target_url)
```

## Troubleshooting

### Issue: Broken notifications not being detected
**Solution:** Ensure `is_object_deleted` property is correctly checking all model types.

### Issue: Auto-archive not working
**Solution:** Check that views are catching and handling exceptions properly.

### Issue: Too many broken notifications
**Solution:** 
1. Run cleanup command with `--dry-run` first
2. Investigate why objects are being deleted
3. Consider implementing soft-delete pattern

## Performance Considerations

- `is_object_deleted` checks can be expensive for large notification lists
- Consider caching broken notification status
- Regular cleanup prevents database bloat
- Auto-archive on access spreads cleanup load

## Future Improvements

1. **Notification Soft Delete**
   - Mark notifications as "expired" instead of checking every time
   - Batch check and mark expired notifications

2. **Dashboard Widget**
   - Show count of broken notifications to admins
   - One-click cleanup from admin panel

3. **User Settings**
   - Allow users to auto-archive broken notifications
   - Configurable age threshold

4. **Analytics**
   - Track which notification types break most often
   - Alert when broken notification rate exceeds threshold

## Support

For issues or questions:
1. Check Django logs for error messages
2. Run cleanup script in dry-run mode
3. Review this documentation
4. Contact system administrator

---

**Last Updated:** 2025-01-18
**Version:** 1.0
**Author:** Rovo Dev
