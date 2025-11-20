from django.core.management.base import BaseCommand
from django.utils import timezone
from jobs.models import Job


class Command(BaseCommand):
    help = 'Deactivate expired job postings'

    def handle(self, *args, **options):
        count = Job.deactivate_expired_jobs()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deactivated {count} expired job(s)')
        )
