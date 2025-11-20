from django.core.management.base import BaseCommand
from users.models import CustomUser


class Command(BaseCommand):
    help = 'Set role_selected=True for all existing users who already have roles'

    def handle(self, *args, **options):
        # Get all users where role_selected is False but they have a role
        users = CustomUser.objects.filter(role_selected=False)
        
        count = 0
        for user in users:
            # If user has a role (not empty), mark as selected
            if user.role:
                user.role_selected = True
                user.save(update_fields=['role_selected'])
                count += 1
                self.stdout.write(f'✅ Updated user: {user.username} (role: {user.role})')
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully updated {count} users'))
