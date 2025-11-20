from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.gis.db import models as gis_models

class ServiceCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name

class ServicePost(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
    ]
    
    headline = models.CharField(max_length=255)
    description = models.TextField()
    availability = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='service_posts')
    address = models.CharField(max_length=255)
    location = gis_models.PointField(null=True, blank=True, srid=4326)
    pricing = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price in PHP")
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_posts")
    admin_notes = models.TextField(blank=True, help_text="Internal admin notes")  

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.headline)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("services:servicepost_detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.headline

class ServicePostImage(models.Model):
    service_post = models.ForeignKey(ServicePost, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='service_images/')

    def __str__(self):
        return f"Image for {self.service_post.headline}"


class ServiceReview(models.Model):
    """Model for service post reviews/ratings with comments"""
    RATING_CHOICES = [
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]
    
    service_post = models.ForeignKey(ServicePost, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_reviews')
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField(help_text="Share your experience with this service")
    is_flagged = models.BooleanField(default=False, help_text="Flagged by moderation system")
    is_hidden = models.BooleanField(default=False, help_text="Hidden by admin or auto-removal")
    flagged_words = models.CharField(max_length=500, blank=True, help_text="Words that triggered moderation")
    report_count = models.IntegerField(default=0, help_text="Number of times reported by users")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, help_text="Admin moderation notes")
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['service_post', 'reviewer']  # One review per user per service
        
    def __str__(self):
        return f"Review by {self.reviewer.get_full_name()} on {self.service_post.headline}"
    
    def check_auto_removal(self):
        """Auto-remove if reported 3+ times by different users"""
        if self.report_count >= 3:
            self.is_hidden = True
            self.save()
            return True
        return False


class ServiceReviewReport(models.Model):
    """Track who reported which review to prevent duplicate reports"""
    review = models.ForeignKey(ServiceReview, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='service_review_reports')
    reason = models.TextField(help_text="Reason for reporting this review")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'reporter']  # One report per user per review
        ordering = ['-created_at']
        
    def __str__(self):
        return f"Report by {self.reporter.get_full_name()} on review {self.review.id}"
