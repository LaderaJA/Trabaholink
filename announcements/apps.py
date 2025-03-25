from django.apps import AppConfig

class AnnouncementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "announcements"

    def ready(self):
        import announcements.signals  # Ensure this line is added

