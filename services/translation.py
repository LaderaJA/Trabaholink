from modeltranslation.translator import translator, TranslationOptions
from .models import ServiceCategory, ServicePost, ServiceReview, ServiceReviewReport


class ServiceCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


class ServicePostTranslationOptions(TranslationOptions):
    fields = ('headline', 'description', 'availability', 'address', 'admin_notes')


class ServiceReviewTranslationOptions(TranslationOptions):
    fields = ('comment', 'admin_notes')


class ServiceReviewReportTranslationOptions(TranslationOptions):
    fields = ('reason',)


# Register models
translator.register(ServiceCategory, ServiceCategoryTranslationOptions)
translator.register(ServicePost, ServicePostTranslationOptions)
translator.register(ServiceReview, ServiceReviewTranslationOptions)
translator.register(ServiceReviewReport, ServiceReviewReportTranslationOptions)
