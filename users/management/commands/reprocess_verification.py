"""
Management command to re-process verification with updated OCR.

Usage:
    python manage.py reprocess_verification <user_id>
    python manage.py reprocess_verification --all-pending
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.services.verification import VerificationPipeline
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Re-process identity verification with updated OCR (color-aware for PhilSys)'

    def add_arguments(self, parser):
        parser.add_argument(
            'user_id',
            nargs='?',
            type=int,
            help='User ID to re-process'
        )
        parser.add_argument(
            '--all-pending',
            action='store_true',
            help='Re-process all pending verifications'
        )
        parser.add_argument(
            '--all-failed',
            action='store_true',
            help='Re-process all failed verifications'
        )

    def handle(self, *args, **options):
        user_id = options.get('user_id')
        all_pending = options.get('all_pending')
        all_failed = options.get('all_failed')

        if user_id:
            # Re-process single user
            self.reprocess_user(user_id)
        elif all_pending:
            # Re-process all pending
            self.reprocess_all_pending()
        elif all_failed:
            # Re-process all failed
            self.reprocess_all_failed()
        else:
            self.stdout.write(self.style.ERROR(
                'Please provide a user_id or use --all-pending or --all-failed'
            ))

    def reprocess_user(self, user_id):
        """Re-process verification for a single user."""
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User {user_id} not found'))
            return

        if not user.id_image or not user.selfie_image:
            self.stdout.write(self.style.ERROR(
                f'User {user_id} has no ID or selfie images uploaded'
            ))
            return

        self.stdout.write(f'\n{"="*80}')
        self.stdout.write(f'Re-processing verification for User ID: {user_id}')
        self.stdout.write(f'Name: {user.get_full_name()}')
        self.stdout.write(f'ID Type: {user.id_type}')
        self.stdout.write(f'Current Status: {user.verification_status}')
        self.stdout.write(f'{"="*80}\n')

        # Run verification pipeline
        pipeline = VerificationPipeline()
        
        try:
            self.stdout.write('Running verification pipeline...')
            result = pipeline.run(user)
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Verification completed!'))
            self.stdout.write(f'Status: {result.status}')
            self.stdout.write(f'Similarity Score: {result.similarity_score}')
            
            if result.extracted_data:
                self.stdout.write(f'\nExtracted Data:')
                for key, value in result.extracted_data.items():
                    if key != 'raw_text':  # Skip raw text (too long)
                        self.stdout.write(f'  - {key}: {value}')
            
            if result.notes:
                self.stdout.write(f'\nNotes:')
                for note in result.notes:
                    self.stdout.write(f'  • {note}')
            
            self.stdout.write(f'\n{"="*80}\n')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Verification failed: {e}'))
            logger.exception(f'Failed to reprocess user {user_id}')

    def reprocess_all_pending(self):
        """Re-process all pending verifications."""
        users = User.objects.filter(
            verification_status='pending'
        ).exclude(
            id_image=''
        ).exclude(
            selfie_image=''
        )

        count = users.count()
        self.stdout.write(f'\nFound {count} pending verifications to re-process\n')

        for idx, user in enumerate(users, 1):
            self.stdout.write(f'\n[{idx}/{count}] Processing User ID: {user.id}')
            self.reprocess_user(user.id)

        self.stdout.write(self.style.SUCCESS(f'\n✅ Completed re-processing {count} verifications'))

    def reprocess_all_failed(self):
        """Re-process all failed verifications."""
        users = User.objects.filter(
            verification_status='failed'
        ).exclude(
            id_image=''
        ).exclude(
            selfie_image=''
        )

        count = users.count()
        self.stdout.write(f'\nFound {count} failed verifications to re-process\n')

        for idx, user in enumerate(users, 1):
            self.stdout.write(f'\n[{idx}/{count}] Processing User ID: {user.id}')
            self.reprocess_user(user.id)

        self.stdout.write(self.style.SUCCESS(f'\n✅ Completed re-processing {count} verifications'))
