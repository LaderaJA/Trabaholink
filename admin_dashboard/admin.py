from django.contrib import admin
from .models import ModeratedWord, Report

@admin.register(ModeratedWord)
class ModeratedWordAdmin(admin.ModelAdmin):
    list_display = ('word', 'is_banned', 'flagged_count')
    list_filter = ('is_banned',)
    search_fields = ('word',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'reported_user', 'job_posting', 'report_type', 'status', 'created_at')
    list_filter = ('status', 'report_type')
    search_fields = ('user__username', 'reported_user__username', 'job_posting__title', 'report_type')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
