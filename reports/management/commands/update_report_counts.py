"""
Management command to update report counts for existing users and jobs.
Run this after migrating to the new reporting system.

Usage: python manage.py update_report_counts
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from reports.models import Report
from users.models import CustomUser
from jobs.models import Job


class Command(BaseCommand):
    help = 'Update report counts for all users and jobs based on existing reports'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting report count update...'))
        
        # Update user report counts
        self.stdout.write('\nUpdating user report counts...')
        user_count = 0
        for user in CustomUser.objects.all():
            # Count unique reporters for this user
            count = Report.objects.filter(
                reported_user=user
            ).values('reporter').distinct().count()
            
            if count != user.report_count:
                user.report_count = count
                user.save(update_fields=['report_count'])
                user_count += 1
                
                if count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {user.username}: {count} reports')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nUpdated {user_count} users')
        )
        
        # Update job report counts
        self.stdout.write('\nUpdating job report counts...')
        job_count = 0
        for job in Job.objects.all():
            # Count unique reporters for this job
            count = Report.objects.filter(
                reported_post=job
            ).values('reporter').distinct().count()
            
            if count != job.report_count:
                job.report_count = count
                job.save(update_fields=['report_count'])
                job_count += 1
                
                if count > 0:
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ Job #{job.id} "{job.title}": {count} reports')
                    )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nUpdated {job_count} jobs')
        )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Report count update completed!'))
        self.stdout.write(f'  - Users updated: {user_count}')
        self.stdout.write(f'  - Jobs updated: {job_count}')
        self.stdout.write('='*60)
