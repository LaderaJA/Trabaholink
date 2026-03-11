from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        import users.signals  # Import user signals (including guide status)
        import announcements.signals
        import jobs.signals
        import messaging.signals
