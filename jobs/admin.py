from django.contrib import admin
from .models import Job, ProgressLog, JobApplication, JobCategory, JobImage, Contract

admin.site.register(Job)
admin.site.register(JobCategory)
admin.site.register(JobApplication)
admin.site.register(JobImage)
admin.site.register(Contract)
admin.site.register(ProgressLog)

