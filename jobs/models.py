from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class JobCategory(models.Model):
    """Categories of jobs (e.g., plumbing, carpentry, cleaning)."""
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Job(models.Model):
    """Model for job postings."""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posted_jobs")
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name="jobs")
    budget = models.DecimalField(max_digits=10, decimal_places=2)

    # 🔹 Location Fields
    municipality = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    subdivision = models.CharField(max_length=100, blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    house_number = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    job_picture = models.ImageField(upload_to='job_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.owner.username}"

class JobApplication(models.Model):
    """Model for job applications by workers."""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_applications")

    cover_letter = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Accepted", "Accepted"), ("Rejected", "Rejected")],
        default="Pending"
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.worker.username} applied for {self.job.title}"

class Contract(models.Model):
    """Model to track jobs that have been awarded."""
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="contract")
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contracts")
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="client_contracts")
    status = models.CharField(
        max_length=20,
        choices=[("Ongoing", "Ongoing"), ("Completed", "Completed"), ("Cancelled", "Cancelled")],
        default="Ongoing"
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Contract for {self.job.title} - {self.worker.username}"
