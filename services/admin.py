from django.contrib import admin
from .models import ServicePost, ServicePostImage, ServiceCategory

admin.site.register(ServicePost)
admin.site.register(ServicePostImage)
admin.site.register(ServiceCategory)