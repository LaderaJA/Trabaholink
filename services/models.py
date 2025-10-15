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
