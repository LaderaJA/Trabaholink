from django.core.management.base import BaseCommand
from admin_dashboard.models import ModeratedWord

class Command(BaseCommand):
    help = 'Add common Filipino and English profanity to banned words list'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing banned words before adding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            ModeratedWord.objects.filter(is_banned=True).delete()
            self.stdout.write(self.style.WARNING('Cleared all existing banned words'))

        # Common Filipino profanity (add more as needed)
        filipino_words = [
            'gago', 'putang', 'putangina', 'bobo', 'tanga', 'tarantado',
            'ulol', 'puta', 'tangina', 'leche', 'yawa', 'pokpok',
            'hayop', 'animal', 'peste', 'buwisit', 'hinayupak'
        ]

        # Common English profanity (add more as needed)
        english_words = [
            'fuck', 'shit', 'bitch', 'ass', 'asshole', 'damn',
            'crap', 'bastard', 'dick', 'pussy', 'cock', 'whore',
            'slut', 'fag', 'nigger', 'cunt', 'motherfucker'
        ]

        all_words = filipino_words + english_words
        added_count = 0
        skipped_count = 0

        for word in all_words:
            obj, created = ModeratedWord.objects.get_or_create(
                word=word.lower(),
                defaults={'is_banned': True}
            )
            if created:
                added_count += 1
                self.stdout.write(self.style.SUCCESS(f'Added banned word: {word}'))
            else:
                skipped_count += 1
                if not obj.is_banned:
                    obj.is_banned = True
                    obj.save()
                    self.stdout.write(self.style.SUCCESS(f'Enabled banned word: {word}'))
                else:
                    self.stdout.write(f'Skipped existing word: {word}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: Added {added_count} words, Skipped {skipped_count} existing words'
            )
        )
