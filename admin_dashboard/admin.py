from django.contrib import admin
from .models import ModeratedWord

# Note: Report admin has been moved to reports/admin.py

@admin.register(ModeratedWord)
class ModeratedWordAdmin(admin.ModelAdmin):
    list_display = ('word', 'is_banned', 'flagged_count')
    list_filter = ('is_banned',)
    search_fields = ('word',)
