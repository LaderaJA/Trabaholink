from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job


class Command(BaseCommand):
    help = 'Archive job postings that have exceeded their posting duration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived without actually archiving',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        now = timezone.now()
        
        # Find all active jobs that have expired
        expired_jobs = Job.objects.filter(
            is_active=True,
            expires_at__lte=now
        )
        
        count = expired_jobs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired job postings found.'))
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would archive {count} expired job posting(s):')
            )
            for job in expired_jobs:
                self.stdout.write(
                    f'  - Job #{job.id}: "{job.title}" (expired at {job.expires_at})'
                )
        else:
            # Archive the expired jobs
            expired_jobs.update(is_active=False)
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully archived {count} expired job posting(s).')
            )
            for job in expired_jobs:
                self.stdout.write(
                    f'  - Archived Job #{job.id}: "{job.title}"'
                )
