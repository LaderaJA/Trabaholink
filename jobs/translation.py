from modeltranslation.translator import translator, TranslationOptions
from .models import JobCategory, Job, JobApplication, Contract


class JobCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


class JobTranslationOptions(TranslationOptions):
    fields = ('title', 'description', 'tasks', 'required_skills')


class JobApplicationTranslationOptions(TranslationOptions):
    fields = ('message', 'cover_letter', 'experience', 'certifications', 'additional_notes')


class ContractTranslationOptions(TranslationOptions):
    fields = ('job_title', 'job_description', 'terms', 'notes', 'termination_reason')


# Register models
translator.register(JobCategory, JobCategoryTranslationOptions)
translator.register(Job, JobTranslationOptions)
translator.register(JobApplication, JobApplicationTranslationOptions)
translator.register(Contract, ContractTranslationOptions)
