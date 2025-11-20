from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job


class Command(BaseCommand):
    help = 'Mark expired job postings as inactive'

    def handle(self, *args, **options):
        now = timezone.now()
        expired_jobs = Job.objects.filter(
            is_active=True,
            expires_at__lte=now
        )
        
        count = expired_jobs.count()
        if count > 0:
            expired_jobs.update(is_active=False)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully closed {count} expired job(s)')
            )
        else:
            self.stdout.write(self.style.SUCCESS('No expired jobs found'))
