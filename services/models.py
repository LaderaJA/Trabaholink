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
    headline = models.CharField(max_length=255)
    description = models.TextField()
    availability = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='service_posts')
    address = models.CharField(max_length=255)
    location = gis_models.PointField(null=True, blank=True, srid=4326)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    worker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="service_posts")  

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
