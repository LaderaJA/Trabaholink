"""
Management command to clean up notifications with broken/deleted references
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up notifications with broken references to deleted objects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Archive notifications older than this many days with broken references (default: 30)'
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete broken notifications instead of archiving them'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        days = options['days']
        delete_mode = options['delete']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(self.style.NOTICE(f'Scanning for notifications with broken references...'))
        
        # Get all notifications with object_id (those that reference other objects)
        notifications = Notification.objects.filter(object_id__isnull=False)
        
        broken_count = 0
        archived_count = 0
        deleted_count = 0
        
        for notification in notifications:
            if notification.is_object_deleted:
                broken_count += 1
                
                # Only process notifications older than cutoff date
                if notification.created_at < cutoff_date:
                    if dry_run:
                        self.stdout.write(
                            f'[DRY RUN] Would {"delete" if delete_mode else "archive"} notification {notification.id}: '
                            f'{notification.message} (created: {notification.created_at})'
                        )
                    else:
                        if delete_mode:
                            notification.delete()
                            deleted_count += 1
                            self.stdout.write(
                                self.style.WARNING(f'Deleted notification {notification.id}: {notification.message}')
                            )
                        else:
                            notification.archive()
                            archived_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(f'Archived notification {notification.id}: {notification.message}')
                            )
        
        # Summary
        self.stdout.write(self.style.NOTICE('\n' + '='*60))
        self.stdout.write(self.style.NOTICE('Summary:'))
        self.stdout.write(self.style.NOTICE(f'Total notifications with broken references: {broken_count}'))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'Would {"delete" if delete_mode else "archive"}: {broken_count} notifications'))
            self.stdout.write(self.style.WARNING('Run without --dry-run to apply changes'))
        else:
            if delete_mode:
                self.stdout.write(self.style.SUCCESS(f'Deleted: {deleted_count} notifications'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Archived: {archived_count} notifications'))
        
        self.stdout.write(self.style.NOTICE('='*60))
