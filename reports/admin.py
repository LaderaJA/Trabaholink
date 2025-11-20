from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Enhanced admin interface for the Report model"""
    
    list_display = (
        'id',
        'reporter_link',
        'report_type',
        'target_link',
        'status_badge',
        'has_screenshot',
        'created_at',
        'quick_actions'
    )
    
    list_filter = (
        'status',
        'created_at',
    )
    
    search_fields = (
        'reporter__username',
        'reported_user__username',
        'reported_post__title',
        'reason'
    )
    
    readonly_fields = ('created_at', 'reviewed_at', 'screenshot_preview')
    
    fieldsets = (
        ('Report Information', {
            'fields': ('reporter', 'reported_user', 'reported_post', 'reason', 'status')
        }),
        ('Evidence', {
            'fields': ('screenshot', 'screenshot_preview'),
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    actions = ['mark_as_reviewed', 'mark_as_resolved', 'mark_as_dismissed']
    
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    actions = ['mark_as_reviewed', 'mark_as_resolved', 'mark_as_dismissed']
    
    def reporter_link(self, obj):
        """Display clickable link to reporter's profile"""
        url = reverse('admin:users_customuser_change', args=[obj.reporter.pk])
        return format_html('<a href="{}">{}</a>', url, obj.reporter.username)
    reporter_link.short_description = 'Reporter'
    
    def target_link(self, obj):
        """Display clickable link to the reported target (user or post)"""
        if obj.reported_user:
            url = reverse('admin:users_customuser_change', args=[obj.reported_user.pk])
            badge_color = '#dc3545' if not obj.reported_user.is_active else '#28a745'
            status_icon = '🔴' if not obj.reported_user.is_active else '🟢'
            return format_html(
                '<a href="{}" style="color: {};">{} {} (Reports: {})</a>',
                url,
                badge_color,
                status_icon,
                obj.reported_user.username,
                obj.reported_user.report_count
            )
        elif obj.reported_post:
            url = reverse('admin:jobs_job_change', args=[obj.reported_post.pk])
            badge_color = '#dc3545' if not obj.reported_post.is_active else '#28a745'
            status_icon = '🔴' if not obj.reported_post.is_active else '🟢'
            return format_html(
                '<a href="{}" style="color: {};">{} {} (Reports: {})</a>',
                url,
                badge_color,
                status_icon,
                obj.reported_post.title[:50],
                obj.reported_post.report_count
            )
        return '-'
    target_link.short_description = 'Reported Target'
    
    def status_badge(self, obj):
        """Display status with color-coded badge"""
        colors = {
            'pending': '#ffc107',
            'reviewed': '#17a2b8',
            'resolved': '#28a745',
            'dismissed': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def report_summary(self, obj):
        """Display a comprehensive summary of the report"""
        if obj.reported_user:
            target_info = f"""
                <strong>Reported User:</strong> {obj.reported_user.username}<br>
                <strong>User Status:</strong> {'🔴 Deactivated' if not obj.reported_user.is_active else '🟢 Active'}<br>
                <strong>Total Reports Against User:</strong> {obj.reported_user.report_count}<br>
            """
        elif obj.reported_post:
            target_info = f"""
                <strong>Reported Post:</strong> {obj.reported_post.title}<br>
                <strong>Post Owner:</strong> {obj.reported_post.owner.username}<br>
                <strong>Post Status:</strong> {'🔴 Deactivated' if not obj.reported_post.is_active else '🟢 Active'}<br>
                <strong>Total Reports Against Post:</strong> {obj.reported_post.report_count}<br>
            """
        else:
            target_info = "<strong>No target specified</strong><br>"
        
        return format_html(
            """
            <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
                <strong>Reporter:</strong> {}<br>
                {}
                <strong>Report Date:</strong> {}<br>
                <strong>Status:</strong> {}<br>
            </div>
            """,
            obj.reporter.username,
            target_info,
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            obj.get_status_display()
        )
    report_summary.short_description = 'Report Summary'
    
    def mark_as_reviewed(self, request, queryset):
        """Mark selected reports as reviewed"""
        updated = queryset.update(
            status='reviewed',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} report(s) marked as reviewed.')
    mark_as_reviewed.short_description = 'Mark as Reviewed'
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected reports as resolved"""
        updated = queryset.update(
            status='resolved',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} report(s) marked as resolved.')
    mark_as_resolved.short_description = 'Mark as Resolved'
    
    def mark_as_dismissed(self, request, queryset):
        """Mark selected reports as dismissed"""
        updated = queryset.update(
            status='dismissed',
            reviewed_at=timezone.now(),
            reviewed_by=request.user
        )
        self.message_user(request, f'{updated} report(s) marked as dismissed.')
    mark_as_dismissed.short_description = 'Mark as Dismissed'
    
    def has_screenshot(self, obj):
        """Display if report has screenshot evidence"""
        if obj.screenshot:
            return format_html(
                '<span style="color: #28a745; font-size: 1.2rem;">📷</span>'
            )
        return format_html('<span style="color: #6c757d;">-</span>')
    has_screenshot.short_description = 'Evidence'
    
    def screenshot_preview(self, obj):
        """Display screenshot preview in admin"""
        if obj.screenshot:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width: 400px; max-height: 300px; border-radius: 8px; border: 2px solid #dee2e6;" />'
                '</a><br><small>Click to view full size</small>',
                obj.screenshot.url,
                obj.screenshot.url
            )
        return format_html('<span style="color: #6c757d;">No screenshot uploaded</span>')
    screenshot_preview.short_description = 'Screenshot Preview'
    
    def quick_actions(self, obj):
        """Display quick action buttons"""
        actions_html = ''
        
        # Link to reported user
        if obj.reported_user:
            user_url = reverse('admin:users_customuser_change', args=[obj.reported_user.pk])
            actions_html += format_html(
                '<a href="{}" class="button" style="background: #3b82f6; color: white; padding: 5px 10px; '
                'border-radius: 4px; text-decoration: none; margin-right: 5px; display: inline-block; font-size: 0.85rem;">'
                '<i class="bi bi-person"></i> View User</a>',
                user_url
            )
        
        # Link to reported post
        if obj.reported_post:
            post_url = reverse('admin:jobs_job_change', args=[obj.reported_post.pk])
            actions_html += format_html(
                '<a href="{}" class="button" style="background: #10b981; color: white; padding: 5px 10px; '
                'border-radius: 4px; text-decoration: none; margin-right: 5px; display: inline-block; font-size: 0.85rem;">'
                '<i class="bi bi-briefcase"></i> View Job</a>',
                post_url
            )
        
        # Link to screenshot if available
        if obj.screenshot:
            actions_html += format_html(
                '<a href="{}" target="_blank" class="button" style="background: #f59e0b; color: white; padding: 5px 10px; '
                'border-radius: 4px; text-decoration: none; display: inline-block; font-size: 0.85rem;">'
                '<i class="bi bi-image"></i> Evidence</a>',
                obj.screenshot.url
            )
        
        return format_html(actions_html)
    quick_actions.short_description = 'Quick Actions'
    
    def save_model(self, request, obj, form, change):
        """Auto-fill reviewed_by and reviewed_at when status changes"""
        if change and 'status' in form.changed_data:
            if obj.status in ['reviewed', 'resolved', 'dismissed']:
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)
