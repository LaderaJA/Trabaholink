from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

class Skill(models.Model):
    """Model for user skills."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('client', 'Client'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    job_coverage = models.CharField(max_length=255, blank=True, null=True) 
    is_verified_philsys = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    jobs_posted = models.ManyToManyField('jobs.Job', related_name='customuser_jobs_posted', blank=True)
    applications = models.ManyToManyField('jobs.JobApplication', related_name='customuser_applications', blank=True)

    connections = models.ManyToManyField('self', symmetrical=False, related_name='connected_users', blank=True)
    skills = models.ManyToManyField('Skill', related_name='customuser_skills', blank=True)

    def __str__(self):
        return self.username
    
    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return "/static/images/default_profile.png"
