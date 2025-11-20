from django.contrib import admin
from .models import ServicePost, ServicePostImage, ServiceCategory, ServiceReview, ServiceReviewReport


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'service_post', 'reviewer', 'rating', 'is_flagged', 'is_hidden', 'report_count', 'created_at']
    list_filter = ['rating', 'is_flagged', 'is_hidden', 'created_at']
    search_fields = ['comment', 'reviewer__email', 'service_post__headline']
    readonly_fields = ['created_at', 'updated_at', 'report_count']
    list_editable = ['is_hidden']
    actions = ['hide_reviews', 'unhide_reviews', 'flag_reviews', 'unflag_reviews']
    
    fieldsets = (
        ('Review Information', {
            'fields': ('service_post', 'reviewer', 'rating', 'comment')
        }),
        ('Moderation', {
            'fields': ('is_flagged', 'is_hidden', 'flagged_words', 'report_count', 'admin_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def hide_reviews(self, request, queryset):
        count = queryset.update(is_hidden=True)
        self.message_user(request, f'{count} review(s) hidden successfully.')
    hide_reviews.short_description = "Hide selected reviews"
    
    def unhide_reviews(self, request, queryset):
        count = queryset.update(is_hidden=False)
        self.message_user(request, f'{count} review(s) unhidden successfully.')
    unhide_reviews.short_description = "Unhide selected reviews"
    
    def flag_reviews(self, request, queryset):
        count = queryset.update(is_flagged=True)
        self.message_user(request, f'{count} review(s) flagged successfully.')
    flag_reviews.short_description = "Flag selected reviews"
    
    def unflag_reviews(self, request, queryset):
        count = queryset.update(is_flagged=False)
        self.message_user(request, f'{count} review(s) unflagged successfully.')
    unflag_reviews.short_description = "Unflag selected reviews"


@admin.register(ServiceReviewReport)
class ServiceReviewReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'review', 'reporter', 'created_at']
    list_filter = ['created_at']
    search_fields = ['reason', 'reporter__email', 'review__comment']
    readonly_fields = ['created_at']
    

admin.site.register(ServicePost)
admin.site.register(ServicePostImage)
admin.site.register(ServiceCategory)