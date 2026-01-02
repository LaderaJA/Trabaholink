from django.contrib import admin
from .models import Announcement

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("title", "posted_by", "is_active", "created_at")
    list_editable = ("is_active",)
    list_filter = ("is_active", "created_at")
    search_fields = ("title", "description")
