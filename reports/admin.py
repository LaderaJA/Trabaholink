from django.contrib import admin
from .models import BannedWord, Report

admin.site.register(BannedWord)
admin.site.register(Report)
