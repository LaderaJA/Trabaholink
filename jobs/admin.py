from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import render
from .models import Job, ProgressLog, JobApplication, JobCategory, JobImage, Contract, JobOffer, JobProgress, Feedback, WorkerAvailability


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Job with report tracking"""
    
    list_display = (
        'id',
        'title',
        'owner',
        'category',
        'is_active',
        'report_count_badge',
        'created_at'
    )
    
    list_filter = (
        'is_active',
        'category',
        'created_at',
        'urgency'
    )
    
    search_fields = ('title', 'description', 'owner__username')
    
    readonly_fields = ('report_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'title', 'description', 'category', 'budget', 'is_active')
        }),
        ('Location', {
            'fields': ('municipality', 'barangay', 'subdivision', 'street', 'house_number', 'latitude', 'longitude')
        }),
        ('Job Details', {
            'fields': ('tasks', 'duration', 'schedule', 'start_datetime', 'number_of_workers', 'urgency')
        }),
        ('Reports & Moderation', {
            'fields': ('report_count',),
            'description': 'This job posting has received reports. Click "View Reports" button below to see details.'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def report_count_badge(self, obj):
        """Display report count with color-coded badge"""
        if obj.report_count == 0:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">0</span>'
            )
        elif obj.report_count < 3:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">{}</span>',
                obj.report_count
            )
        elif obj.report_count < 10:
            return format_html(
                '<span style="background-color: #fd7e14; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">{} ⚠️</span>',
                obj.report_count
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">{} 🔴</span>',
                obj.report_count
            )
    report_count_badge.short_description = 'Reports'
    report_count_badge.admin_order_field = 'report_count'
    
    def get_urls(self):
        """Add custom URL for viewing reports"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:job_id>/reports/',
                self.admin_site.admin_view(self.view_job_reports),
                name='view_job_reports',
            ),
        ]
        return custom_urls + urls
    
    def view_job_reports(self, request, job_id):
        """Custom view to display all reports for a specific job"""
        from reports.models import Report
        job = Job.objects.get(pk=job_id)
        reports = Report.objects.filter(reported_post=job).select_related(
            'reporter', 'reviewed_by'
        ).order_by('-created_at')
        
        context = {
            'job': job,
            'reports': reports,
            'title': f'Reports for Job: {job.title}',
            'opts': self.model._meta,
        }
        return render(request, 'admin/jobs/view_job_reports.html', context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add 'View Reports' button to the change view"""
        extra_context = extra_context or {}
        try:
            job = Job.objects.get(pk=object_id)
            if job.report_count > 0:
                extra_context['show_view_reports_button'] = True
                extra_context['view_reports_url'] = reverse(
                    'admin:view_job_reports',
                    args=[object_id]
                )
        except Job.DoesNotExist:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


admin.site.register(JobCategory)
admin.site.register(JobApplication)
admin.site.register(JobImage)
admin.site.register(Contract)
admin.site.register(ProgressLog)
admin.site.register(JobOffer)
admin.site.register(JobProgress)
admin.site.register(Feedback)

@admin.register(WorkerAvailability)
class WorkerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['worker', 'get_day_name', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available', 'worker']
    search_fields = ['worker__username', 'worker__first_name', 'worker__last_name']
    ordering = ['worker', 'day_of_week', 'start_time']
    
    def get_day_name(self, obj):
        return dict(obj.DAYS_OF_WEEK)[obj.day_of_week]
    get_day_name.short_description = 'Day'

