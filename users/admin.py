from django.contrib import admin
from .models import CustomUser, Skill

admin.site.register(CustomUser)

class SkillVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'status', 'submitted_at')
    list_filter = ('status', 'submitted_at')
    search_fields = ('user__username', 'name')

admin.site.register(Skill, SkillVerificationAdmin)