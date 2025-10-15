from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry


GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
]


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('client', 'Client'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    contact_number = models.CharField(max_length=15, blank=True)
    bio = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)  # new field
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)  # new field
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    cover_photo = models.CharField(max_length=50, default='default1', blank=True)  # Cover photo choice or custom upload
    cover_photo_custom = models.ImageField(upload_to='cover_photos/', blank=True, null=True)  # Custom uploaded cover
    job_title = models.CharField(max_length=100, blank=True, null=True)  # Professional job title
    job_coverage = models.CharField(max_length=255, blank=True, null=True) 
    is_verified_philsys = models.BooleanField(default=False)
    location = gis_models.PointField(null=True, blank=True, geography=True) 
    is_worker = models.BooleanField(default=True)  
    notification_location = gis_models.PointField(null=True, blank=True)  # New field for notification location
    identity_document = models.ImageField(upload_to='identity_docs/', null=True, blank=True)
    identity_verification_status = models.CharField(
        max_length=20,
        choices=[("pending", "Pending"), ("verified", "Verified"), ("skipped", "Skipped")],
        default="pending"
    )
    
    # eKYC Verification Fields
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('unverified', 'Unverified'),
            ('pending', 'Pending Review'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected')
        ],
        default='unverified'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    jobs_posted = models.ManyToManyField('jobs.Job', related_name='customuser_jobs_posted', blank=True)
    applications = models.ManyToManyField('jobs.JobApplication', related_name='customuser_applications', blank=True)
    connections = models.ManyToManyField('self', symmetrical=False, related_name='connected_users', blank=True)
    

    def __str__(self):
        return self.username
        
    def get_location_display(self):
        """Return a human-readable location from the coordinates"""
        if not self.location:
            print("DEBUG: No location data available")
            return "Location not specified"
        
        try:
            print(f"DEBUG: Raw location data: {self.location}")
            print(f"DEBUG: Location type: {type(self.location)}")
            
            from geopy.geocoders import Nominatim
            from geopy.exc import GeocoderTimedOut, GeocoderServiceError
            
            # Get the coordinates
            lat = float(self.location.y)
            lon = float(self.location.x)
            print(f"DEBUG: Coordinates - Lat: {lat}, Lon: {lon}")
            
            # Initialize geocoder with a more specific user agent and timeout
            geolocator = Nominatim(
                user_agent="traba_holink_app/1.0",
                timeout=10
            )
            
            # Try to get the address
            try:
                print("DEBUG: Attempting to reverse geocode...")
                location = geolocator.reverse(f"{lat}, {lon}", exactly_one=True, language='en')
                if location and hasattr(location, 'address'):
                    print(f"DEBUG: Found address: {location.address}")
                    return location.address
                else:
                    print("DEBUG: No address found for coordinates")
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                print(f"DEBUG: Geocoding error: {str(e)}")
            except Exception as e:
                print(f"DEBUG: Unexpected error during geocoding: {str(e)}")
            
            # If reverse geocoding fails, return coordinates in a cleaner format
            coords = f"{lat:.6f}°N, {lon:.6f}°E"
            print(f"DEBUG: Returning coordinates: {coords}")
            return coords
            
        except ImportError as e:
            print(f"DEBUG: Geopy import error: {str(e)}")
            return f"{self.location.y:.6f}°N, {self.location.x:.6f}°E"
        except Exception as e:
            print(f"DEBUG: Unexpected error in get_location_display: {str(e)}")
            return "Location not available"
    
    def get_profile_picture_url(self):
        if self.profile_picture:
            return self.profile_picture.url
        return "/static/images/default_profile.png"
    
    @property
    def pending_skill_verification_count(self):
        return self.skill_verifications.filter(status='pending').count()


class Skill(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('unverified', 'Unverified'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_verifications', default=1)
    name = models.CharField(max_length=100, help_text="e.g. Driving")
    description = models.TextField(blank=True, help_text="Brief description of your skill")
    proof = models.FileField(upload_to='skill_proofs/', help_text="Upload proof such as a license or certificate", default=None, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(default=now)
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"


# New model: Education
class Education(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='education')
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.degree} from {self.institution}"


# New model: Experience (Work Experience)
class Experience(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='experiences')
    job_title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.job_title} at {self.company}"


class CompletedJobGallery(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="completed_jobs"
    )
    image = models.ImageField(upload_to="completed_jobs/")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Gallery Item for {self.user.username}"


class AccountVerification(models.Model):
    """Model to track eKYC verification submissions"""
    
    ID_TYPE_CHOICES = [
        ('philsys', 'PhilSys ID'),
        ('drivers_license', "Driver's License"),
        ('passport', 'Passport'),
        ('umid', 'UMID'),
        ('sss', 'SSS ID'),
        ('voters', "Voter's ID"),
        ('prc', 'PRC ID'),
        ('postal', 'Postal ID'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_submissions'
    )
    
    # Personal Information
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField()
    address = models.TextField()
    contact_number = models.CharField(max_length=15)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    
    # ID Information
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES)
    id_image_front = models.ImageField(upload_to='verification/ids/')
    id_image_back = models.ImageField(upload_to='verification/ids/', null=True, blank=True)
    
    # Selfie Verification
    selfie_image = models.ImageField(upload_to='verification/selfies/')
    
    # Status and Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_verifications'
    )
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Verification for {self.user.username} - {self.status}"
