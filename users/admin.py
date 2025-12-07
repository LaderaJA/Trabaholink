from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.utils import timezone
from django.shortcuts import render
from .models import CustomUser, Skill, AccountVerification, EmailOTP, PhilSysVerification, ActivityLog, UserGuideStatus


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    """Enhanced admin interface for CustomUser with report tracking"""
    
    list_display = (
        'username',
        'email',
        'role',
        'is_active',
        'report_count_badge',
        'is_verified',
        'date_joined'
    )
    
    list_filter = (
        'role',
        'is_active',
        'is_verified',
        'verification_status',
        'date_joined'
    )
    
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    readonly_fields = ('report_count', 'date_joined', 'last_login')
    
    fieldsets = (
        ('Account Information', {
            'fields': ('username', 'email', 'password', 'role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'contact_number', 'bio', 'address', 'gender', 'date_of_birth')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_status', 'verification_date')
        }),
        ('Reports & Moderation', {
            'fields': ('report_count',),
            'description': 'This user has received reports. Click "View Reports" button below to see details.'
        }),
        ('Timestamps', {
            'fields': ('date_joined', 'last_login'),
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
        elif obj.report_count < 5:
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">{}</span>',
                obj.report_count
            )
        elif obj.report_count < 15:
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
                '<int:user_id>/reports/',
                self.admin_site.admin_view(self.view_user_reports),
                name='view_user_reports',
            ),
        ]
        return custom_urls + urls
    
    def view_user_reports(self, request, user_id):
        """Custom view to display all reports for a specific user"""
        from reports.models import Report
        user = CustomUser.objects.get(pk=user_id)
        reports = Report.objects.filter(reported_user=user).select_related(
            'reporter', 'reviewed_by'
        ).order_by('-created_at')
        
        context = {
            'user': user,
            'reports': reports,
            'title': f'Reports for {user.username}',
            'opts': self.model._meta,
        }
        return render(request, 'admin/users/view_user_reports.html', context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add 'View Reports' button to the change view"""
        extra_context = extra_context or {}
        try:
            user = CustomUser.objects.get(pk=object_id)
            if user.report_count > 0:
                extra_context['show_view_reports_button'] = True
                extra_context['view_reports_url'] = reverse(
                    'admin:view_user_reports',
                    args=[object_id]
                )
        except CustomUser.DoesNotExist:
            pass
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    """Admin interface for viewing OTP codes during testing"""
    list_display = ('email', 'username', 'otp_code', 'is_verified', 'attempts', 'created_at', 'is_expired_display')
    list_filter = ('is_verified', 'created_at', 'role')
    search_fields = ('email', 'username')
    readonly_fields = ('created_at', 'password_hash')
    ordering = ('-created_at',)
    
    def is_expired_display(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">✗ Expired</span>')
        return format_html('<span style="color: green;">✓ Valid</span>')
    is_expired_display.short_description = 'Status'
    
    fieldsets = (
        ('Email Verification', {
            'fields': ('email', 'otp_code', 'is_verified', 'attempts', 'created_at')
        }),
        ('User Data (Temporary)', {
            'fields': ('username', 'role', 'password_hash')
        }),
    )

class SkillVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__username', 'name')

admin.site.register(Skill, SkillVerificationAdmin)


@admin.register(AccountVerification)
class AccountVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'id_type', 'status', 'submitted_at', 'action_buttons')
    list_filter = ('status', 'id_type', 'submitted_at')
    search_fields = ('user__username', 'full_name', 'contact_number')
    readonly_fields = ('submitted_at', 'reviewed_at', 'id_preview', 'selfie_preview')
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'date_of_birth', 'gender', 'address', 'contact_number')
        }),
        ('ID Information', {
            'fields': ('id_type', 'id_image_front', 'id_image_back', 'id_preview')
        }),
        ('Selfie Verification', {
            'fields': ('selfie_image', 'selfie_preview')
        }),
        ('Review Status', {
            'fields': ('status', 'rejection_reason', 'submitted_at', 'reviewed_at', 'reviewed_by')
        }),
    )
    
    def id_preview(self, obj):
        html = ''
        if obj.id_image_front:
            html += f'<div><strong>Front:</strong><br><img src="{obj.id_image_front.url}" style="max-width:400px;"/></div>'
        if obj.id_image_back:
            html += f'<div style="margin-top:10px;"><strong>Back:</strong><br><img src="{obj.id_image_back.url}" style="max-width:400px;"/></div>'
        return format_html(html) if html else '-'
    id_preview.short_description = 'ID Images'
    
    def selfie_preview(self, obj):
        if obj.selfie_image:
            return format_html(f'<img src="{obj.selfie_image.url}" style="max-width:300px;"/>')
        return '-'
    selfie_preview.short_description = 'Selfie'
    
    def action_buttons(self, obj):
        if obj.status == 'pending':
            # Link to the admin dashboard verification detail page instead
            return format_html(
                '<a class="button" href="/admin/identity-verifications/{}/">View Details</a>',
                obj.pk
            )
        return obj.get_status_display()
    action_buttons.short_description = 'Actions'
    
    def save_model(self, request, obj, form, change):
        if change and obj.status in ['approved', 'rejected']:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
            
            # Update user verification status
            if obj.status == 'approved':
                obj.user.is_verified = True
                obj.user.verification_status = 'verified'
                obj.user.verification_date = timezone.now()
                obj.user.date_of_birth = obj.date_of_birth
                obj.user.save()
                
                # Send notification to user
                from notifications.models import Notification
                Notification.objects.create(
                    user=obj.user,
                    message="Your account verification has been approved! You now have a verified badge.",
                    notif_type="verification_approved"
                )
            elif obj.status == 'rejected':
                obj.user.verification_status = 'rejected'
                obj.user.save()
                
                # Build detailed rejection message with mismatch information
                from users.models import VerificationLog
                
                rejection_message = "Your account verification was not approved."
                
                # Get the most recent verification log for this user
                recent_log = VerificationLog.objects.filter(
                    user=obj.user,
                    result__in=['failed', 'manual_review']
                ).order_by('-created_at').first()
                
                if recent_log and recent_log.notes:
                    # Extract mismatch information from notes
                    mismatches = []
                    notes_lines = recent_log.notes.split('\n')
                    
                    in_mismatch_section = False
                    for line in notes_lines:
                        if 'Data mismatches found:' in line:
                            in_mismatch_section = True
                            continue
                        if in_mismatch_section:
                            if line.strip().startswith('- '):
                                # Extract the mismatch detail
                                mismatch = line.strip()[2:]  # Remove "- " prefix
                                # Make it more user-friendly
                                if 'mismatch:' in mismatch.lower():
                                    mismatches.append(mismatch)
                            elif line.strip() and not line.strip().startswith('Warning:'):
                                # End of mismatch section
                                break
                    
                    if mismatches:
                        rejection_message += "\n\nInformation mismatches detected:"
                        for mismatch in mismatches:
                            # Clean up the mismatch message
                            if 'First name mismatch:' in mismatch:
                                rejection_message += f"\n• {mismatch.replace('First name mismatch:', 'First Name:')}"
                            elif 'Last name mismatch:' in mismatch:
                                rejection_message += f"\n• {mismatch.replace('Last name mismatch:', 'Last Name:')}"
                            elif 'Full name mismatch:' in mismatch:
                                rejection_message += f"\n• {mismatch.replace('Full name mismatch:', 'Full Name:')}"
                            elif 'Date of birth mismatch:' in mismatch:
                                rejection_message += f"\n• {mismatch.replace('Date of birth mismatch:', 'Date of Birth:')}"
                            else:
                                rejection_message += f"\n• {mismatch}"
                        
                        rejection_message += "\n\nPlease ensure your profile information matches your ID exactly and try again."
                    else:
                        rejection_message += " Please check the reason and try again."
                else:
                    # Fallback to rejection_reason if available
                    if obj.rejection_reason:
                        rejection_message += f"\n\nReason: {obj.rejection_reason}"
                    else:
                        rejection_message += " Please check the reason and try again."
                
                # Send notification to user
                from notifications.models import Notification
                Notification.objects.create(
                    user=obj.user,
                    message=rejection_message,
                    notif_type="verification_rejected"
                )
        
        super().save_model(request, obj, form, change)


@admin.register(PhilSysVerification)
class PhilSysVerificationAdmin(admin.ModelAdmin):
    """Admin interface for PhilSys QR verification records"""
    
    list_display = (
        'user', 
        'status_badge', 
        'pcn_masked', 
        'verified',
        'response_time_display',
        'retry_count',
        'created_at',
        'user_consented'
    )
    
    list_filter = (
        'status', 
        'verified', 
        'user_consented',
        'created_at',
        'verification_source'
    )
    
    search_fields = (
        'user__username', 
        'user__email', 
        'pcn_hash',
        'qr_payload_hash'
    )
    
    readonly_fields = (
        'user',
        'qr_payload_encrypted',
        'qr_payload_hash',
        'pcn_masked',
        'pcn_hash',
        'status',
        'verified',
        'verification_message',
        'verification_source',
        'verification_timestamp',
        'response_time',
        'retry_count',
        'last_retry_at',
        'error_details',
        'screenshot_preview',
        'preprocessing_applied',
        'extracted_fields',
        'created_at',
        'updated_at',
        'ip_address',
        'user_agent',
        'user_consented',
        'consent_timestamp'
    )
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_consented', 'consent_timestamp')
        }),
        ('PhilSys Data (Encrypted)', {
            'fields': (
                'pcn_masked',
                'pcn_hash',
                'qr_payload_hash',
                'qr_payload_encrypted'
            ),
            'description': 'QR payload is encrypted. Only hashes and masked values are shown.'
        }),
        ('Verification Result', {
            'fields': (
                'status',
                'verified',
                'verification_message',
                'verification_source',
                'verification_timestamp',
                'response_time'
            )
        }),
        ('Extraction Details', {
            'fields': (
                'preprocessing_applied',
                'extracted_fields'
            ),
            'classes': ('collapse',)
        }),
        ('Error & Retry Information', {
            'fields': (
                'retry_count',
                'last_retry_at',
                'error_details',
                'screenshot_preview'
            ),
            'classes': ('collapse',)
        }),
        ('Audit Trail', {
            'fields': (
                'created_at',
                'updated_at',
                'ip_address',
                'user_agent'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Display status with color-coded badge"""
        colors = {
            'pending': '#ffc107',
            'processing': '#17a2b8',
            'verified': '#28a745',
            'failed': '#dc3545',
            'error': '#dc3545',
            'timeout': '#6c757d'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def response_time_display(self, obj):
        """Display response time in human-readable format"""
        if obj.response_time:
            return f"{obj.response_time:.2f}s"
        return '-'
    response_time_display.short_description = 'Response Time'
    
    def screenshot_preview(self, obj):
        """Display screenshot if available"""
        if obj.screenshot_path:
            try:
                return format_html(
                    '<a href="{}" target="_blank">View Screenshot</a><br>'
                    '<img src="{}" style="max-width: 600px; margin-top: 10px;"/>',
                    obj.screenshot_path,
                    obj.screenshot_path
                )
            except (IOError, OSError) as e:
                logger.debug(f"Failed to display screenshot image: {e}")
                return format_html(
                    '<a href="{}" target="_blank">View Screenshot</a>',
                    obj.screenshot_path
                )
        return '-'
    screenshot_preview.short_description = 'Verification Screenshot'
    
    def has_add_permission(self, request):
        """Prevent manual creation of verification records"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of verification records for audit trail"""
        return request.user.is_superuser
    
    actions = ['export_verification_data']
    
    def export_verification_data(self, request, queryset):
        """Export verification data for analysis"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="philsys_verifications.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'User', 'Status', 'Verified', 'PCN Masked', 'Response Time',
            'Retry Count', 'Created At', 'Consented'
        ])
        
        for obj in queryset:
            writer.writerow([
                obj.user.username,
                obj.status,
                obj.verified,
                obj.pcn_masked,
                obj.response_time or '',
                obj.retry_count,
                obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                obj.user_consented
            ])
        
        return response
    export_verification_data.short_description = 'Export selected verifications to CSV'


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin interface for activity logs"""
    list_display = ('user', 'activity_type', 'description', 'timestamp')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'description')
    readonly_fields = ('user', 'activity_type', 'description', 'timestamp', 'content_type', 'object_id', 'metadata')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserGuideStatus)
class UserGuideStatusAdmin(admin.ModelAdmin):
    """Admin interface for User Guide Status."""
    
    list_display = [
        'user',
        'auto_popup_enabled',
        'last_page_viewed',
        'last_step_completed',
        'total_guides_viewed',
        'last_interaction',
    ]
    
    list_filter = [
        'auto_popup_enabled',
        'last_interaction',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'last_page_viewed',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'last_interaction',
    ]
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Guide Settings', {
            'fields': ('auto_popup_enabled',)
        }),
        ('Progress Tracking', {
            'fields': (
                'last_page_viewed',
                'last_step_completed',
                'pages_completed',
                'total_guides_viewed',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_interaction'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent manual creation - should be auto-created via signals."""
        return False