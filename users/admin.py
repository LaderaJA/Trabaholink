from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import CustomUser, Skill, AccountVerification

admin.site.register(CustomUser)

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
            return format_html(
                '<a class="button" href="{}">Approve</a> '
                '<a class="button" href="{}">Reject</a>',
                reverse('admin:approve_verification', args=[obj.pk]),
                reverse('admin:reject_verification', args=[obj.pk])
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
                
                # Send notification to user
                from notifications.models import Notification
                Notification.objects.create(
                    user=obj.user,
                    message="Your account verification was not approved. Please check the reason and try again.",
                    notif_type="verification_rejected"
                )
        
        super().save_model(request, obj, form, change)