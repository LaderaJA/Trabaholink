from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from better_profanity import profanity
from admin_dashboard.utils import load_banned_words
from django.urls import reverse
from django.utils import timezone
from simple_history.models import HistoricalRecords
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance
from notifications.models import Notification


CustomUser = get_user_model()

class JobCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Job(models.Model):
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="posted_jobs")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True, default="")
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name="jobs")
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    
    municipality = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    subdivision = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    house_number = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    job_picture = models.ImageField(upload_to='job_images/', blank=True, null=True)
    
    # New fields:
    tasks = models.TextField(default= "job to be done", help_text="List specific tasks expected from the worker.")
    duration = models.CharField(max_length=100, default="e.g. 2 days, 1 week",help_text="e.g. 2 days, 1 week")
    schedule = models.CharField(max_length=255, default="e.g. M-F, 9AM-5PM", help_text="e.g. M-F, 9AM-5PM")
    start_datetime = models.DateTimeField(null=True, blank=True)
    tools_provided = models.BooleanField(default=False)
    materials_provided = models.BooleanField(default=False)
    required_skills = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[("Cash", "Cash"), ("GCash", "GCash"), ("Bank Transfer", "Bank Transfer")],
        default="Cash"
    )
    payment_schedule = models.CharField(max_length=100, blank=True)
    urgency = models.CharField(
        max_length=50,
        choices=[("Flexible", "Flexible"), ("Urgent", "Urgent"), ("Specific Date", "Specific Date")],
        default="Flexible"
    )
    number_of_workers = models.PositiveIntegerField(default=1)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    location = gis_models.PointField(null=True, blank=True, geography=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} - {self.owner.username}"
    
    @property
    def post_type(self):
        return "Job"

    def get_absolute_url(self):
        return reverse("jobs:job_detail", kwargs={"id": self.id})

    def save(self, *args, **kwargs):
        # Load banned words
        banned_words = load_banned_words()

        # Censor single words using better-profanity
        profanity.load_censor_words([word for word in banned_words if ' ' not in word])
        self.description = profanity.censor(self.description)

        for phrase in banned_words:
            if ' ' in phrase:  
                self.description = self.description.replace(phrase, '*' * len(phrase))

        super().save(*args, **kwargs)

class JobImage(models.Model):
    job = models.ForeignKey(Job, related_name='jobimage_set', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='job_images/')
    
    def __str__(self):
        return f"Image for {self.job.title}"

class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="job_applications")
    cover_letter = models.TextField(blank=True, null=True)
    proposed_rate = models.CharField(max_length=100, null=True, blank=True)
    available_start_date = models.DateField(null=True, blank=True)
    expected_duration = models.CharField(max_length=100, blank=True)
    experience = models.TextField(blank=True)
    Other_link = models.URLField(blank=True, null=True, help_text="Link to Facebook, LinkedIn, or other profiles")
    certifications = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Accepted", "Accepted"), ("Rejected", "Rejected")],
        default="Pending"
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()  

    def __str__(self):
        return f"{self.worker.username} applied for {self.job.title}"

class Contract(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="contract")
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="contracts")
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="client_contracts")
    
    # Updated status choices including a "Draft" state:
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Accepted", "Accepted"),
        ("In Progress", "In Progress"),
        ("Submitted for Review", "Submitted for Review"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled")
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Draft")
    
    payment_status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("In Escrow", "In Escrow"), ("Released", "Released")],
        default="Pending"
    )
    
    is_revision_requested = models.BooleanField(default=False)
    
    # Negotiation fields for draft contracts:
    is_draft = models.BooleanField(default=True)
    scope_of_work = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    deliverables = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Feedback fields
    feedback_by_client = models.TextField(blank=True, null=True)
    rating_by_client = models.IntegerField(blank=True, null=True)
    feedback_by_worker = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    history = HistoricalRecords()  

    # NEW: Field to indicate worker acceptance
    worker_accepted = models.BooleanField(default=False)
    
    def finalize_contract(self):
        self.is_draft = False
        self.status = "Accepted"
        self.updated_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"Contract for {self.job.title} - {self.worker.username}"


class ProgressLog(models.Model):
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="progress_logs")
    status = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

@receiver(post_save, sender=Job)
def notify_users_about_new_job(sender, instance, created, **kwargs):
    if created:
        nearby_users = CustomUser.objects.filter(job_coverage=instance.municipality)
        for user in nearby_users:
            subject = "New Job Posting Near You!"
            message = f"A new job '{instance.title}' has been posted near your location.\n\nCheck it out on Trabaholink."
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

@receiver(post_save, sender=Job)
def notify_workers_about_new_job(sender, instance, created, **kwargs):
    if created and instance.location:
        # Filter workers whose notification_location is set and within 5 km
        nearby_workers = CustomUser.objects.filter(
            is_worker=True,
            notification_location__isnull=False,
            notification_location__distance_lte=(instance.location, D(km=5))
        ).annotate(distance=Distance("notification_location", instance.location)).order_by("distance")
        
        for worker in nearby_workers:
            Notification.objects.create(
                user=worker,
                message=f"A new job '{instance.title}' has been posted near you. Click to view details.",
                notif_type="job_post",
                object_id=instance.pk,
            )
