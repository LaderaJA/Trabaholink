import uuid
import os

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.conf import settings
from django.utils.timezone import now
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import GEOSGeometry
from .validators import validate_cv_file


GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
]

VALID_ID_CHOICES = [
    ('philsys', 'PhilSys National ID'),
    ('drivers_license', "Driver's License"),
    ('passport', 'Passport'),
    ('umid', 'UMID'),
    ('sss', 'SSS ID'),
    ('voters', "Voter's ID"),
    ('prc', 'PRC ID'),
    ('postal', 'Postal ID'),
]

def _build_uuid_path(prefix: str, filename: str) -> str:
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    new_filename = f"{uuid.uuid4()}.{extension}" if extension else f"{uuid.uuid4()}"
    return f"verification/{prefix}/{new_filename}"


def id_image_upload_path(instance, filename):
    return _build_uuid_path("ids", filename)


def selfie_image_upload_path(instance, filename):
    return _build_uuid_path("selfies", filename)


def cv_file_upload_path(instance, filename):
    """
    Generate secure upload path for CV files.
    Sanitizes filename and uses UUID for security.
    """
    # Get file extension
    ext = os.path.splitext(filename)[1].lower()
    # Sanitize original filename (remove special characters, keep only alphanumeric and spaces)
    base_name = os.path.splitext(filename)[0]
    safe_name = ''.join(c for c in base_name if c.isalnum() or c in (' ', '-', '_'))
    safe_name = safe_name[:50]  # Limit length
    # Create unique filename with UUID
    unique_filename = f"{uuid.uuid4()}_{safe_name}{ext}"
    return f"user_cvs/{unique_filename}"


class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('worker', 'Worker'),
        ('client', 'Client'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    role_selected = models.BooleanField(default=False, help_text="Has user explicitly selected their role?")
    profile_completed = models.BooleanField(default=False, help_text="Has user completed initial profile setup?")
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
    philsys_verified_at = models.DateTimeField(null=True, blank=True)
    philsys_pcn_masked = models.CharField(max_length=20, blank=True)  # Masked PCN for display
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
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('manual_review', 'Manual Review'),
    ]

    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    id_type = models.CharField(max_length=32, choices=VALID_ID_CHOICES, blank=True)
    id_image = models.ImageField(upload_to=id_image_upload_path, null=True, blank=True)
    selfie_image = models.ImageField(upload_to=selfie_image_upload_path, null=True, blank=True)
    verification_score = models.FloatField(null=True, blank=True)
    verification_log = models.TextField(blank=True)
    
    # Additional verification fields (from eKYC process)
    face_detected = models.BooleanField(default=False)
    ocr_confidence_score = models.IntegerField(default=0)
    ocr_raw_text = models.TextField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_users')
    
    # CV/Resume Upload
    cv_file = models.FileField(
        upload_to=cv_file_upload_path,
        null=True,
        blank=True,
        validators=[validate_cv_file],
        help_text='Upload your CV/Resume (PDF, DOC, or DOCX format, max 5MB)'
    )
    cv_uploaded_at = models.DateTimeField(null=True, blank=True, help_text='Timestamp of last CV upload')

    groups = models.ManyToManyField(Group, related_name="customuser_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="customuser_permissions", blank=True)

    jobs_posted = models.ManyToManyField('jobs.Job', related_name='customuser_jobs_posted', blank=True)
    applications = models.ManyToManyField('jobs.JobApplication', related_name='customuser_applications', blank=True)
    connections = models.ManyToManyField('self', symmetrical=False, related_name='connected_users', blank=True)
    
    # Reporting system field
    report_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique reports received by this user"
    )

    def __str__(self):
        return str(self.username) if self.username else f"User {self.pk}"
        
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
    id_type = models.CharField(max_length=32, choices=VALID_ID_CHOICES)
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
    notes = models.TextField(blank=True, help_text='Internal notes about verification')
    
    # Face matching fields
    face_match_score = models.FloatField(
        null=True, 
        blank=True, 
        help_text='Face similarity score (0-1)'
    )
    face_match_metadata = models.JSONField(
        null=True, 
        blank=True, 
        help_text='Metadata from face matching process'
    )
    
    class Meta:
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Verification for {self.user.username} - {self.status}"


class VerificationLog(models.Model):
    """Audit log for automated/manual eKYC verification outcomes."""

    PROCESS_TYPE_CHOICES = [
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
    ]

    RESULT_CHOICES = CustomUser.VERIFICATION_STATUS_CHOICES

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='verification_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    similarity_score = models.FloatField(null=True, blank=True)
    process_type = models.CharField(max_length=20, choices=PROCESS_TYPE_CHOICES, default='auto')
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Verification log for {self.user.username} at {self.created_at:%Y-%m-%d %H:%M:%S}"


class PhilSysVerification(models.Model):
    """
    Model to track PhilSys QR code verification attempts and results.
    Stores encrypted QR payload and verification metadata.
    """
    
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='philsys_verifications'
    )
    
    # Encrypted QR data (never store plaintext)
    qr_payload_encrypted = models.TextField(blank=True)
    qr_payload_hash = models.CharField(max_length=64, db_index=True)  # SHA-256 hash
    
    # PhilSys Card Number (masked for display)
    pcn_masked = models.CharField(max_length=20, blank=True)  # e.g., "1234-****-****-5678"
    pcn_hash = models.CharField(max_length=64, blank=True, db_index=True)  # SHA-256 hash
    
    # Verification status and results
    status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    verified = models.BooleanField(default=False)
    verification_message = models.TextField(blank=True)
    
    # Web verification metadata
    verification_source = models.CharField(
        max_length=50, 
        default='philsys_web_automation'
    )
    verification_timestamp = models.DateTimeField(null=True, blank=True)
    response_time = models.FloatField(null=True, blank=True)  # In seconds
    
    # Retry tracking
    retry_count = models.IntegerField(default=0)
    last_retry_at = models.DateTimeField(null=True, blank=True)
    
    # Error tracking
    error_details = models.TextField(blank=True)
    screenshot_path = models.CharField(max_length=255, blank=True)
    
    # Preprocessing metadata
    preprocessing_applied = models.JSONField(default=list, blank=True)
    extracted_fields = models.JSONField(default=dict, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Consent tracking
    user_consented = models.BooleanField(default=False)
    consent_timestamp = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['qr_payload_hash']),
            models.Index(fields=['pcn_hash']),
            models.Index(fields=['created_at']),
            models.Index(fields=['verified']),
        ]
    
    def __str__(self):
        return f"PhilSys verification for {self.user.username} - {self.status}"
    
    def mark_as_verified(self):
        """Mark verification as successful."""
        from django.utils import timezone
        self.status = 'verified'
        self.verified = True
        self.verification_timestamp = timezone.now()
        self.save(update_fields=['status', 'verified', 'verification_timestamp', 'updated_at'])
    
    def mark_as_failed(self, message: str = ""):
        """Mark verification as failed."""
        self.status = 'failed'
        self.verified = False
        self.verification_message = message
        self.save(update_fields=['status', 'verified', 'verification_message', 'updated_at'])
    
    def increment_retry(self):
        """Increment retry counter."""
        from django.utils import timezone
        self.retry_count += 1
        self.last_retry_at = timezone.now()
        self.save(update_fields=['retry_count', 'last_retry_at', 'updated_at'])


class EmailOTP(models.Model):
    """
    Model to store email OTP codes for account verification.
    OTPs are hashed before storage for security.
    """
    email = models.EmailField()
    otp_code = models.CharField(max_length=128)  # Increased to store hashed OTP
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)  # Track failed attempts
    
    # Store user data temporarily until email is verified
    username = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=255)  # Hashed password
    role = models.CharField(max_length=10, default='client')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'is_verified']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"OTP for {self.email} - {'Verified' if self.is_verified else 'Pending'}"
    
    def is_expired(self):
        """Check if OTP has expired (10 minutes)"""
        from django.utils import timezone
        from datetime import timedelta
        expiry_time = self.created_at + timedelta(minutes=settings.OTP_EXPIRY_MINUTES)
        return timezone.now() > expiry_time
    
    def increment_attempts(self):
        """Increment failed verification attempts"""
        self.attempts += 1
        self.save()


# Import ActivityLog model
from .activity_logger import ActivityLog, log_activity


class PrivacySettings(models.Model):
    """
    Privacy settings for user profiles.
    Controls what information is visible and to whom.
    """
    VISIBILITY_CHOICES = [
        ('public', 'Public - Anyone can view my profile'),
        ('connections', 'Connections Only - Only my connections can view'),
        ('private', 'Private - Only I can view my profile'),
    ]
    
    user = models.OneToOneField(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='privacy_settings'
    )
    
    # Profile visibility
    profile_visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='public',
        help_text='Who can view your profile'
    )
    
    # Contact information visibility
    show_email = models.BooleanField(
        default=True,
        help_text='Show email address on profile'
    )
    show_phone = models.BooleanField(
        default=True,
        help_text='Show phone number on profile'
    )
    
    # Activity privacy
    show_activity = models.BooleanField(
        default=True,
        help_text='Show your activity in public feeds'
    )
    allow_search_engines = models.BooleanField(
        default=False,
        help_text='Allow search engines to index your profile'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Privacy Settings'
        verbose_name_plural = 'Privacy Settings'
    
    def __str__(self):
        return f"Privacy settings for {self.user.username}"
    
    @staticmethod
    def get_or_create_for_user(user):
        """Get or create privacy settings for a user with default values"""
        settings, created = PrivacySettings.objects.get_or_create(
            user=user,
            defaults={
                'profile_visibility': 'public',
                'show_email': True,
                'show_phone': True,
                'show_activity': True,
                'allow_search_engines': False,
            }
        )
        return settings


class UserGuideStatus(models.Model):
    """
    Tracks user guide status and preferences across the platform.
    
    This model stores:
    - Whether auto-popup is enabled for the user
    - Last page where guide was viewed
    - Last step completed on that page
    - Timestamp of last interaction
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='guide_status',
        verbose_name='User',
        help_text='The user this guide status belongs to'
    )
    
    auto_popup_enabled = models.BooleanField(
        default=True,
        verbose_name='Auto-popup Enabled',
        help_text='If True, guide will automatically appear on page load'
    )
    
    last_page_viewed = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Last Page Viewed',
        help_text='URL name of the last page where guide was opened'
    )
    
    last_step_completed = models.IntegerField(
        default=0,
        verbose_name='Last Step Completed',
        help_text='Last step number completed on the last viewed page'
    )
    
    pages_completed = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Pages Completed',
        help_text='Dict of {page_name: {completed: bool, last_step: int, timestamp: str}}'
    )
    
    total_guides_viewed = models.IntegerField(
        default=0,
        verbose_name='Total Guides Viewed',
        help_text='Count of how many times user has opened any guide'
    )
    
    last_interaction = models.DateTimeField(
        auto_now=True,
        verbose_name='Last Interaction',
        help_text='Timestamp of last guide interaction'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Created At'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Updated At'
    )
    
    class Meta:
        verbose_name = 'User Guide Status'
        verbose_name_plural = 'User Guide Statuses'
        db_table = 'users_user_guide_status'
        indexes = [
            models.Index(fields=['user'], name='idx_guide_user'),
            models.Index(fields=['auto_popup_enabled'], name='idx_guide_auto_popup'),
            models.Index(fields=['last_interaction'], name='idx_guide_last_interaction'),
        ]
    
    def __str__(self):
        return f"Guide Status: {self.user.username} (Auto-popup: {self.auto_popup_enabled})"
    
    def mark_page_completed(self, page_name, last_step=None):
        """Mark a specific page's guide as completed."""
        from django.utils import timezone
        if not self.pages_completed:
            self.pages_completed = {}
        
        self.pages_completed[page_name] = {
            'completed': True,
            'last_step': last_step or 0,
            'timestamp': timezone.now().isoformat()
        }
        self.last_page_viewed = page_name
        if last_step is not None:
            self.last_step_completed = last_step
        self.save()
    
    def update_progress(self, page_name, step):
        """Update progress for a specific page without marking complete."""
        from django.utils import timezone
        if not self.pages_completed:
            self.pages_completed = {}
        
        if page_name not in self.pages_completed:
            self.pages_completed[page_name] = {
                'completed': False,
                'last_step': step,
                'timestamp': timezone.now().isoformat()
            }
        else:
            self.pages_completed[page_name]['last_step'] = step
            self.pages_completed[page_name]['timestamp'] = timezone.now().isoformat()
        
        self.last_page_viewed = page_name
        self.last_step_completed = step
        self.save()
    
    def is_page_completed(self, page_name):
        """Check if a specific page's guide has been completed."""
        if not self.pages_completed:
            return False
        return self.pages_completed.get(page_name, {}).get('completed', False)
    
    def get_page_last_step(self, page_name):
        """Get the last step viewed for a specific page."""
        if not self.pages_completed:
            return 0
        return self.pages_completed.get(page_name, {}).get('last_step', 0)
    
    def increment_view_count(self):
        """Increment the total guides viewed counter."""
        self.total_guides_viewed += 1
        self.save(update_fields=['total_guides_viewed', 'updated_at'])
    
    def disable_auto_popup(self):
        """Disable auto-popup for this user."""
        self.auto_popup_enabled = False
        self.save(update_fields=['auto_popup_enabled', 'updated_at'])
    
    def enable_auto_popup(self):
        """Re-enable auto-popup for this user."""
        self.auto_popup_enabled = True
        self.save(update_fields=['auto_popup_enabled', 'updated_at'])
