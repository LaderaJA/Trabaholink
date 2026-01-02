from modeltranslation.translator import translator, TranslationOptions
from .models import CustomUser


class CustomUserTranslationOptions(TranslationOptions):
    fields = ('bio', 'address', 'job_title', 'job_coverage')


# Register models
translator.register(CustomUser, CustomUserTranslationOptions)
