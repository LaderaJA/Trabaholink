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

# IMPORTANT: Register historical models explicitly for django-simple-history compatibility
# This ensures translation fields are added to HistoricalJob, HistoricalJobApplication, and HistoricalContract
try:
    # Access historical models after main models are registered
    HistoricalJob = Job.history.model
    HistoricalJobApplication = JobApplication.history.model
    HistoricalContract = Contract.history.model
    
    # Register historical models with the same translation options
    translator.register(HistoricalJob, JobTranslationOptions)
    translator.register(HistoricalJobApplication, JobApplicationTranslationOptions)
    translator.register(HistoricalContract, ContractTranslationOptions)
except Exception as e:
    # If historical models aren't available yet (e.g., during initial migrations), ignore
    pass
