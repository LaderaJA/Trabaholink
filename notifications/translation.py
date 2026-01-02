from modeltranslation.translator import translator, TranslationOptions
from .models import Notification


class NotificationTranslationOptions(TranslationOptions):
    fields = ('message',)


# Register models
translator.register(Notification, NotificationTranslationOptions)
