from django.contrib import admin
from .models import Job, ProgressLog, JobApplication, JobCategory, JobImage, Contract, JobOffer, JobProgress, Feedback

admin.site.register(Job)
admin.site.register(JobCategory)
admin.site.register(JobApplication)
admin.site.register(JobImage)
admin.site.register(Contract)
admin.site.register(ProgressLog)
admin.site.register(JobOffer)
admin.site.register(JobProgress)
admin.site.register(Feedback)

