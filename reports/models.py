from django.db import models
from users.models import CustomUser

class BannedWord(models.Model):
    word = models.CharField(max_length=100, unique=True)


class Report(models.Model):
    reported_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reports_received")
    reporter_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reports_made")
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('resolved', 'Resolved')])
    created_at = models.DateTimeField(auto_now_add=True)
