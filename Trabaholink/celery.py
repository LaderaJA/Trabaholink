"""Celery configuration for Trabaholink project."""
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.signals import worker_ready
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')

app = Celery('Trabaholink')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Import simplified OCR task
app.autodiscover_tasks(['users'], related_name='tasks_ocr_simple')

# Import automatic PhilSys verification task
app.autodiscover_tasks(['users'], related_name='tasks_philsys_auto')

# Import schedule tasks for calendar notifications
app.autodiscover_tasks(['jobs'], related_name='tasks_schedule')

# Configure Celery Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'send-daily-schedule-reminders': {
        'task': 'jobs.tasks_schedule.send_daily_schedule_reminders',
        'schedule': crontab(hour=8, minute=0),  # Run every day at 8:00 AM
        'options': {'expires': 3600}  # Expire if not run within 1 hour
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f'Request: {self.request!r}')


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """
    Run when Celery worker starts up.
    Scans for pending PhilSys verifications and queues them for processing.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("🚀 Celery worker started - scanning for pending PhilSys verifications...")
    logger.info("=" * 80)
    
    try:
        from users.tasks_philsys_auto import scan_pending_philsys_verifications
        # Queue the scan task
        scan_pending_philsys_verifications.delay()
        logger.info("✅ Pending PhilSys verification scan queued")
    except Exception as e:
        logger.error(f"❌ Failed to queue pending verification scan: {e}")
