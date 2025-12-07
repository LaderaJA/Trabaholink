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
    duration = models.CharField(max_length=100, default="",help_text="e.g. 2 days, 1 week")
    schedule = models.CharField(max_length=255, default="", help_text="e.g. M-F, 9AM-5PM")
    start_datetime = models.DateTimeField(null=True, blank=True)
    tools_provided = models.BooleanField(default=False)
    materials_provided = models.BooleanField(default=False)
    required_skills = models.TextField(blank=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[("Cash", "Cash")],
        default="Cash"
    )
    payment_schedule = models.CharField(max_length=100, blank=True)
    urgency = models.CharField(
        max_length=50,
        choices=[("Flexible", "Flexible"), ("Urgent", "Urgent"), ("Specific Date", "Specific Date")],
        default="Flexible"
    )
    number_of_workers = models.PositiveIntegerField(default=1)
    vacancies = models.PositiveIntegerField(
        default=1,
        help_text="Number of available positions (auto-decrements when contracts are finalized)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    location = gis_models.PointField(null=True, blank=True, geography=True)
    
    # Posting duration fields
    posting_duration_days = models.PositiveIntegerField(
        default=7,
        help_text="Number of days the job posting will be active (default: 7 days)"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the job posting will automatically be archived"
    )
    
    # Reporting system field
    report_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of unique reports received for this job posting"
    )
    
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} - {self.owner.username}"
    
    @property
    def post_type(self):
        return "Job"

    def get_absolute_url(self):
        return reverse("jobs:job_detail", kwargs={"id": self.id})
    
    def is_expired(self):
        """Check if the job has expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False
    
    def has_vacancies(self):
        """Check if there are available positions"""
        return self.vacancies > 0
    
    def decrement_vacancy(self):
        """Decrease vacancy count by 1 when a contract is finalized"""
        if self.vacancies > 0:
            self.vacancies -= 1
            self.save(update_fields=['vacancies', 'updated_at'])  # Include updated_at to trigger refresh
            # Refresh from database to ensure we have the latest value
            self.refresh_from_db()
            return True
        return False
    
    def get_applicant_count(self):
        """Get real-time count of applicants for this job"""
        return self.applications.exclude(status__iexact='Archived').count()
    
    def get_vacancies_remaining(self):
        """Get remaining vacancies (total vacancies minus finalized contracts)"""
        finalized_count = self.contracts.filter(
            status__in=['Finalized', 'In Progress', 'Accepted', 'Completed']
        ).count()
        return max(0, self.vacancies - finalized_count)
    
    @classmethod
    def deactivate_expired_jobs(cls):
        """Deactivate all expired jobs"""
        from django.utils import timezone
        expired_jobs = cls.objects.filter(
            is_active=True,
            expires_at__lte=timezone.now()
        )
        count = expired_jobs.update(is_active=False)
        return count

    def save(self, *args, **kwargs):
        # Initialize vacancies to match number_of_workers if creating new job
        if not self.pk:
            self.vacancies = self.number_of_workers
        # Load banned words
        banned_words = load_banned_words()

        # Censor single words using better-profanity
        profanity.load_censor_words([word for word in banned_words if ' ' not in word])
        self.description = profanity.censor(self.description)

        for phrase in banned_words:
            if ' ' in phrase:  
                self.description = self.description.replace(phrase, '*' * len(phrase))
        
        # Set expires_at based on posting_duration_days if not already set
        if not self.expires_at and self.posting_duration_days:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=self.posting_duration_days)

        super().save(*args, **kwargs)

class JobImage(models.Model):
    job = models.ForeignKey(Job, related_name='jobimage_set', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='job_images/')
    
    def __str__(self):
        return f"Image for {self.job.title}"

class JobApplication(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="job_applications")
    message = models.TextField(blank=True, null=True, help_text="Optional message to employer")
    cover_letter = models.TextField(blank=True, null=True)
    proposed_rate = models.CharField(max_length=100, null=True, blank=True)
    available_start_date = models.DateField(null=True, blank=True)
    expected_duration = models.CharField(max_length=100, blank=True)
    experience = models.TextField(blank=True)
    Other_link = models.URLField(blank=True, null=True, help_text="Link to Facebook, LinkedIn, or other profiles")
    certifications = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    attach_profile_cv = models.BooleanField(
        default=False, 
        help_text="Whether to attach CV from user profile"
    )

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Withdrawn", "Withdrawn"),
        ("Negotiation", "Negotiation")
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending"
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_shortlisted = models.BooleanField(default=False)
    employer_notes = models.TextField(blank=True, default='', help_text="Internal notes from employer")
    is_viewed = models.BooleanField(default=False)
    viewed_at = models.DateTimeField(null=True, blank=True)
    history = HistoricalRecords()  

    def __str__(self):
        return f"{self.worker.username} applied for {self.job.title}"
    
    def mark_as_viewed(self):
        """Mark application as viewed by employer"""
        if not self.is_viewed:
            from django.utils import timezone
            self.is_viewed = True
            self.viewed_at = timezone.now()
            self.save()
    
    class Meta:
        ordering = ['-applied_at']
        unique_together = ['job', 'worker']

    @property
    def current_contract(self):
        """Return contract linked to this application, if any."""
        contract = getattr(self, "contract", None)
        if contract:
            return contract

        # Query for a contract explicitly linked to this application first
        contract = Contract.objects.filter(application=self).order_by('-created_at').first()
        if contract:
            return contract

        # Only attempt legacy fallback for non-pending applications
        if self.status.lower() in {"negotiation", "accepted", "in progress", "awaiting review", "completed"}:
            return Contract.objects.filter(job=self.job, worker=self.worker).order_by('-created_at').first()

        return None


class JobOffer(models.Model):
    """
    Represents a job offer sent by an employer to a worker.
    This bridges the gap between application acceptance and contract creation.
    """
    application = models.OneToOneField(JobApplication, on_delete=models.CASCADE, related_name="offer")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="offers")
    employer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="sent_offers")
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_offers")
    
    # Offer details
    offered_rate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Offered payment rate")
    proposed_start_date = models.DateField(help_text="Proposed start date for the job")
    proposed_end_date = models.DateField(null=True, blank=True, help_text="Proposed end date (if applicable)")
    work_schedule = models.CharField(max_length=255, blank=True, help_text="e.g., M-F, 9AM-5PM")
    message = models.TextField(help_text="Message from employer to worker")
    terms_and_conditions = models.TextField(blank=True, help_text="Specific terms for this offer")
    
    # Offer status
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Rejected", "Rejected"),
        ("Expired", "Expired"),
        ("Withdrawn", "Withdrawn")
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Offer expiration date")
    responded_at = models.DateTimeField(null=True, blank=True, help_text="When worker responded")
    
    # Worker response
    rejection_reason = models.TextField(blank=True, help_text="Reason for rejection (if applicable)")
    counter_offer_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Counter offer from worker")
    counter_offer_message = models.TextField(blank=True, help_text="Counter offer message from worker")
    
    history = HistoricalRecords()
    
    def __str__(self):
        return f"Offer for {self.worker.username} - {self.job.title}"
    
    def check_worker_availability(self):
        """
        Check if worker is available for this offer's schedule.
        Returns a dict with 'available' (bool), 'conflicts' (list), and 'message' (str).
        """
        from datetime import time as dt_time
        import re
        
        # Parse work_schedule for time information
        start_time = None
        end_time = None
        
        if self.work_schedule:
            time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?'
            match = re.search(time_pattern, self.work_schedule)
            
            if match:
                start_hour = int(match.group(1))
                start_min = int(match.group(2)) if match.group(2) else 0
                start_period = match.group(3).upper() if match.group(3) else None
                
                end_hour = int(match.group(4))
                end_min = int(match.group(5)) if match.group(5) else 0
                end_period = match.group(6).upper() if match.group(6) else None
                
                # Convert to 24-hour format
                if start_period == 'PM' and start_hour != 12:
                    start_hour += 12
                elif start_period == 'AM' and start_hour == 12:
                    start_hour = 0
                    
                if end_period == 'PM' and end_hour != 12:
                    end_hour += 12
                elif end_period == 'AM' and end_hour == 12:
                    end_hour = 0
                
                try:
                    start_time = dt_time(start_hour, start_min)
                    end_time = dt_time(end_hour, end_min)
                except ValueError:
                    pass
        
        # If we don't have time info, assume available (will be set during negotiation)
        if not start_time or not end_time or not self.proposed_start_date:
            return {
                'available': True,
                'conflicts': [],
                'message': 'Schedule details will be finalized during negotiation.'
            }
        
        # Use proposed_end_date or start_date as fallback
        end_date = self.proposed_end_date or self.proposed_start_date
        
        # Check availability
        result = WorkerAvailability.check_availability_for_contract(
            worker=self.worker,
            start_date=self.proposed_start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time
        )
        
        if result['available']:
            return {
                'available': True,
                'conflicts': [],
                'message': 'Worker is available for this schedule.'
            }
        else:
            conflict_msgs = []
            for conflict in result['conflicts'][:5]:
                conflict_msgs.append(f"{conflict['date'].strftime('%a, %b %d')}: {conflict['reason']}")
            
            return {
                'available': False,
                'conflicts': result['conflicts'],
                'message': 'Worker has schedule conflicts:\n' + '\n'.join(conflict_msgs)
            }
    
    def accept_offer(self):
        """Accept the offer and create a dedicated contract for this application"""
        from datetime import time as dt_time
        import re
        
        # Parse work_schedule for time information (e.g., "9AM-5PM" or "09:00-17:00")
        start_time = None
        end_time = None
        
        if self.work_schedule:
            # Try to extract time from schedule string
            # Pattern for formats like "9AM-5PM", "9:00AM-5:00PM", "09:00-17:00"
            time_pattern = r'(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?\s*[-–]\s*(\d{1,2})(?::(\d{2}))?\s*(AM|PM|am|pm)?'
            match = re.search(time_pattern, self.work_schedule)
            
            if match:
                start_hour = int(match.group(1))
                start_min = int(match.group(2)) if match.group(2) else 0
                start_period = match.group(3).upper() if match.group(3) else None
                
                end_hour = int(match.group(4))
                end_min = int(match.group(5)) if match.group(5) else 0
                end_period = match.group(6).upper() if match.group(6) else None
                
                # Convert to 24-hour format if AM/PM specified
                if start_period == 'PM' and start_hour != 12:
                    start_hour += 12
                elif start_period == 'AM' and start_hour == 12:
                    start_hour = 0
                    
                if end_period == 'PM' and end_hour != 12:
                    end_hour += 12
                elif end_period == 'AM' and end_hour == 12:
                    end_hour = 0
                
                try:
                    start_time = dt_time(start_hour, start_min)
                    end_time = dt_time(end_hour, end_min)
                except ValueError:
                    # Invalid time values, keep as None
                    pass
        
        self.status = "Accepted"
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at", "updated_at"])

        # Update application status to negotiation phase
        self.application.status = "Negotiation"
        self.application.save(update_fields=["status", "updated_at"])

        contract = Contract.objects.create(
            job=self.job,
            worker=self.worker,
            client=self.employer,
            application=self.application,
            status="Negotiation",
            job_title=self.job.title,
            job_description=self.job.description,
            agreed_rate=self.offered_rate,
            rate_type="fixed",
            payment_schedule=self.job.payment_schedule or "End of Project",
            duration=self.job.duration or "To be determined",
            schedule=self.work_schedule or self.job.schedule or "To be determined",
            start_date=self.proposed_start_date,
            end_date=self.proposed_end_date,
            start_time=start_time,
            end_time=end_time,
            terms=self.terms_and_conditions or "",
        )

        return contract
    
    def reject_offer(self, reason=""):
        """Reject the offer"""
        self.status = "Rejected"
        self.responded_at = timezone.now()
        self.rejection_reason = reason
        self.save()
        
        # Update application status
        self.application.status = "Rejected"
        self.application.save()
    
    def is_expired(self):
        """Check if offer has expired"""
        if self.expires_at and timezone.now() > self.expires_at:
            if self.status == "Pending":
                self.status = "Expired"
                self.save()
            return True
        return False
    
    class Meta:
        ordering = ['-created_at']


class Contract(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="contracts")
    worker = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="contracts")
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="client_contracts")
    application = models.OneToOneField('JobApplication', on_delete=models.SET_NULL, null=True, blank=True, related_name="contract")
    
    # Updated status choices for new workflow:
    STATUS_CHOICES = [
        ("Negotiation", "Negotiation"),
        ("Finalized", "Finalized"),
        ("In Progress", "In Progress"),
        ("Awaiting Review", "Awaiting Review"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled")
    ]
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="Negotiation")
    
    payment_status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("In Escrow", "In Escrow"), ("Released", "Released")],
        default="Pending"
    )
    
    is_revision_requested = models.BooleanField(default=False)

    # Contract terms (editable during negotiation):
    RATE_TYPE_CHOICES = [
        ("hourly", "Hourly"),
        ("fixed", "Fixed Price"),
    ]
    rate_type = models.CharField(max_length=20, choices=RATE_TYPE_CHOICES, default="fixed")
    job_title = models.CharField(max_length=255, blank=True)
    job_description = models.TextField(blank=True)
    agreed_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_schedule = models.CharField(max_length=30, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    schedule = models.CharField(max_length=255, blank=True)
    start_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True, help_text="Daily start time (e.g., 9:00 AM)")
    end_time = models.TimeField(null=True, blank=True, help_text="Daily end time (e.g., 5:00 PM)")
    notes = models.TextField(blank=True, help_text="Special terms or notes")
    terms = models.TextField(blank=True, help_text="Contract terms and conditions")
    
    # Legacy fields (keep for backward compatibility)
    scope_of_work = models.TextField(blank=True)
    payment_terms = models.TextField(blank=True)
    deliverables = models.TextField(blank=True)
    end_date = models.DateField(null=True, blank=True)
    
    # Feedback fields
    feedback_by_client = models.TextField(blank=True, null=True)
    rating_by_client = models.IntegerField(blank=True, null=True)
    feedback_by_worker = models.TextField(blank=True, null=True)
    rating_by_worker = models.IntegerField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True, help_text="When work actually started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When work was completed")
    
    # Termination/Dispute fields
    termination_requested_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="requested_terminations",
        help_text="User who requested contract termination"
    )
    termination_reason = models.TextField(blank=True, default='', help_text="Reason for termination request")
    termination_requested_at = models.DateTimeField(null=True, blank=True)
    
    history = HistoricalRecords()  

    # Acceptance tracking
    finalized_by_worker = models.BooleanField(default=False)
    finalized_by_employer = models.BooleanField(default=False)
    
    # Legacy fields (keep for backward compatibility)
    worker_accepted = models.BooleanField(default=False)
    client_accepted = models.BooleanField(default=False)
    is_finalized = models.BooleanField(default=False, help_text="True when both parties accept")
    is_draft = models.BooleanField(default=False)
    
    def finalize_contract(self):
        self.is_draft = False
        self.status = "Accepted"
        self.updated_at = timezone.now()
        self.save()
    
    def start_work(self):
        """Mark contract as in progress"""
        self.status = "In Progress"
        self.started_at = timezone.now()
        self.save()
    
    def complete_work(self):
        """Mark contract as completed"""
        self.status = "Submitted for Review"
        self.completed_at = timezone.now()
        self.save()
    
    def request_termination(self, user, reason):
        """Request contract termination"""
        self.termination_requested_by = user
        self.termination_reason = reason
        self.termination_requested_at = timezone.now()
        self.save()
    
    def check_time_conflict(self):
        """Check if this contract conflicts with worker's existing contracts"""
        if not self.start_date or not self.end_date or not self.start_time or not self.end_time:
            return None
        
        # Get all active contracts for this worker (excluding this contract)
        worker_contracts = Contract.objects.filter(
            worker=self.worker,
            status__in=['Finalized', 'In Progress', 'Awaiting Review']
        ).exclude(pk=self.pk)
        
        conflicts = []
        for contract in worker_contracts:
            if not contract.start_date or not contract.end_date or not contract.start_time or not contract.end_time:
                continue
            
            # Check if date ranges overlap
            date_overlap = (
                self.start_date <= contract.end_date and 
                self.end_date >= contract.start_date
            )
            
            if date_overlap:
                # Check if time ranges overlap
                time_overlap = (
                    self.start_time < contract.end_time and 
                    self.end_time > contract.start_time
                )
                
                if time_overlap:
                    conflicts.append({
                        'contract': contract,
                        'job_title': contract.job_title or contract.job.title,
                        'dates': f"{contract.start_date} to {contract.end_date}",
                        'times': f"{contract.start_time.strftime('%I:%M %p')} - {contract.end_time.strftime('%I:%M %p')}"
                    })
        
        return conflicts if conflicts else None
    
    @staticmethod
    def get_worker_schedule(worker, start_date=None, end_date=None):
        """Get all contracts for a worker in a date range"""
        contracts = Contract.objects.filter(
            worker=worker,
            status__in=['Finalized', 'In Progress', 'Awaiting Review', 'Completed']
        ).select_related('job', 'client')
        
        if start_date:
            contracts = contracts.filter(end_date__gte=start_date)
        if end_date:
            contracts = contracts.filter(start_date__lte=end_date)
        
        return contracts.order_by('start_date', 'start_time')
    
    def get_calendar_event_data(self):
        """
        Return contract data in FullCalendar format with DAILY recurring events.
        This creates one event per day showing actual work hours, perfect for week view.
        """
        if not self.start_date or not self.end_date:
            return None
        
        from datetime import datetime, time as dt_time, timedelta
        
        start_time = self.start_time or dt_time(9, 0)  # Default 9:00 AM
        end_time = self.end_time or dt_time(17, 0)  # Default 5:00 PM
        
        events = []
        current_date = self.start_date
        
        # Generate unique color for this contract based on job ID
        color = self._get_contract_color()
        
        # Create one event per day showing daily work hours
        while current_date <= self.end_date:
            events.append({
                'id': f"{self.pk}_{current_date.strftime('%Y%m%d')}",
                'title': self.job_title or self.job.title,
                'start': f"{current_date}T{start_time.strftime('%H:%M:%S')}",
                'end': f"{current_date}T{end_time.strftime('%H:%M:%S')}",
                'backgroundColor': color,
                'borderColor': color,
                'textColor': '#ffffff',
                'extendedProps': {
                    'contractId': self.pk,
                    'status': self.status,
                    'client': self.client.get_full_name() or self.client.username,
                    'rate': str(self.agreed_rate) if self.agreed_rate else 'N/A',
                    'description': self.job_description[:100] if self.job_description else '',
                    'workHours': f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
                }
            })
            current_date += timedelta(days=1)
        
        return events
    
    def _get_status_color(self):
        """Get color based on contract status (kept for backward compatibility)"""
        colors = {
            'Negotiation': '#f59e0b',  # Orange
            'Finalized': '#3b82f6',    # Blue
            'In Progress': '#10b981',  # Green
            'Awaiting Review': '#8b5cf6',  # Purple
            'Completed': '#6b7280',    # Gray
            'Cancelled': '#ef4444'     # Red
        }
        return colors.get(self.status, '#6b7280')
    
    def _get_contract_color(self):
        """
        Generate a unique, distinct color for each contract.
        Uses job ID to ensure same job always gets same color.
        """
        # Palette of distinct, professional colors
        color_palette = [
            '#3b82f6',  # Blue
            '#10b981',  # Green
            '#f59e0b',  # Orange
            '#8b5cf6',  # Purple
            '#ef4444',  # Red
            '#06b6d4',  # Cyan
            '#ec4899',  # Pink
            '#f97316',  # Orange-red
            '#14b8a6',  # Teal
            '#a855f7',  # Purple-pink
            '#84cc16',  # Lime
            '#f43f5e',  # Rose
            '#6366f1',  # Indigo
            '#eab308',  # Yellow
            '#22c55e',  # Green-lime
        ]
        
        # Use job ID to pick color (same job always same color)
        index = self.job.id % len(color_palette)
        return color_palette[index]
    
    def __str__(self):
        return f"Contract for {self.job.title} - {self.worker.username}"


class JobProgress(models.Model):
    """Track job progress updates from worker"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="progress_updates")
    update_text = models.TextField(help_text="Progress update description")
    image = models.ImageField(upload_to='progress_images/', blank=True, null=True, help_text="Optional progress photo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Job Progress Updates"
    
    def __str__(self):
        return f"Progress update for {self.contract.job.title} at {self.created_at}"


class ProgressLog(models.Model):
    """Legacy progress log model - kept for backward compatibility"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="progress_logs")
    status = models.CharField(max_length=50)
    message = models.TextField(blank=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class Feedback(models.Model):
    """Feedback and ratings after job completion"""
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="feedbacks")
    giver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="given_feedbacks")
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="received_feedbacks")
    rating = models.IntegerField(help_text="Rating from 1 to 5")
    message = models.TextField(help_text="Feedback message")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['contract', 'giver']
    
    def __str__(self):
        return f"Feedback from {self.giver.username} for {self.receiver.username} - {self.rating} stars"


@receiver(post_save, sender=Job)
def notify_users_about_new_job(sender, instance, created, **kwargs):
    if created:
        nearby_users = CustomUser.objects.filter(job_coverage=instance.municipality)
        for user in nearby_users:
            try:
                subject = "New Job Posting Near You!"
                message = f"A new job '{instance.title}' has been posted near your location.\n\nCheck it out on Trabaholink."
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
            except Exception as e:
                print(f"Failed to send job notification to {user.email}: {str(e)}")
                continue

@receiver(post_save, sender=Job)
def notify_workers_about_new_job(sender, instance, created, **kwargs):
    if created and instance.location:
        # Filter users whose notification_location is set and within 5 km
        # Exclude the job owner from notifications
        # Note: We check for workers by role, not is_worker field
        nearby_workers = CustomUser.objects.filter(
            role='worker',  # Use role field instead of is_worker
            notification_location__isnull=False,
            notification_location__distance_lte=(instance.location, D(km=5))
        ).exclude(id=instance.owner.id).annotate(distance=Distance("notification_location", instance.location)).order_by("distance")
        
        for worker in nearby_workers:
            Notification.objects.create(
                user=worker,
                message=f"A new job '{instance.title}' has been posted near you. Click to view details.",
                notif_type="job_post",
                object_id=instance.pk,
            )


class WorkerAvailability(models.Model):
    """
    Manage worker's available working hours per day to prevent schedule conflicts.
    Workers can set their preferred working hours for each day of the week.
    """
    DAYS_OF_WEEK = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    worker = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name="work_availability"
    )
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField(help_text="Available start time")
    end_time = models.TimeField(help_text="Available end time")
    is_available = models.BooleanField(default=True, help_text="Toggle availability for this day")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name_plural = "Worker Availabilities"
        unique_together = ['worker', 'day_of_week', 'start_time']
    
    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK)[self.day_of_week]
        return f"{self.worker.username} - {day_name} {self.start_time.strftime('%I:%M %p')} to {self.end_time.strftime('%I:%M %p')}"
    
    def check_conflict_with_contract(self, contract):
        """
        Check if this availability slot conflicts with a contract's schedule.
        Returns True if there's a conflict, False otherwise.
        """
        if not contract.start_time or not contract.end_time:
            return False
        
        # Check if time ranges overlap
        time_overlap = (
            self.start_time < contract.end_time and 
            self.end_time > contract.start_time
        )
        
        return time_overlap
    
    @staticmethod
    def get_worker_availability(worker, day_of_week=None):
        """Get worker's availability schedule"""
        availability = WorkerAvailability.objects.filter(
            worker=worker,
            is_available=True
        )
        
        if day_of_week is not None:
            availability = availability.filter(day_of_week=day_of_week)
        
        return availability.order_by('day_of_week', 'start_time')
    
    @staticmethod
    def check_availability_for_contract(worker, start_date, end_date, start_time, end_time):
        """
        Check if worker is available for the proposed contract schedule.
        Priority: Check TIME conflicts first (most important), then availability slots.
        Returns a dict with 'available' (bool) and 'conflicts' (list of conflicting days).
        """
        from datetime import timedelta
        
        conflicts = []
        current_date = start_date
        
        # Get all active contracts for this worker
        existing_contracts = Contract.objects.filter(
            worker=worker,
            status__in=['Finalized', 'In Progress', 'Awaiting Review']
        ).exclude(start_date__isnull=True).exclude(end_date__isnull=True)
        
        while current_date <= end_date:
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            
            # PRIORITY 1: Check for time conflicts with existing contracts on this date
            has_time_conflict = False
            for contract in existing_contracts:
                # Check if this contract overlaps with current_date
                if contract.start_date <= current_date <= contract.end_date:
                    # Check if times conflict (same date, overlapping times)
                    if contract.start_time and contract.end_time:
                        # Time ranges overlap if: start_time < other.end_time AND end_time > other.start_time
                        if start_time < contract.end_time and end_time > contract.start_time:
                            has_time_conflict = True
                            conflicts.append({
                                'date': current_date,
                                'reason': f'Time conflict with "{contract.job_title or contract.job.title}" ({contract.start_time.strftime("%I:%M %p")} - {contract.end_time.strftime("%I:%M %p")})'
                            })
                            break  # One conflict per day is enough
            
            # Skip further checks if time conflict found (most important)
            if has_time_conflict:
                current_date += timedelta(days=1)
                continue
            
            # PRIORITY 2: Check worker's availability settings for this day
            day_availability = WorkerAvailability.objects.filter(
                worker=worker,
                day_of_week=day_of_week,
                is_available=True
            )
            
            if not day_availability.exists():
                conflicts.append({
                    'date': current_date,
                    'reason': 'Worker not available on this day of week'
                })
            else:
                # Check if requested time falls within any availability slot
                has_matching_slot = False
                for slot in day_availability:
                    # Time must be fully within the slot
                    if start_time >= slot.start_time and end_time <= slot.end_time:
                        has_matching_slot = True
                        break
                
                if not has_matching_slot:
                    # Show available times for this day
                    available_times = [f"{slot.start_time.strftime('%I:%M %p')}-{slot.end_time.strftime('%I:%M %p')}" 
                                      for slot in day_availability]
                    conflicts.append({
                        'date': current_date,
                        'reason': f'Time {start_time.strftime("%I:%M %p")}-{end_time.strftime("%I:%M %p")} not in available slots: {", ".join(available_times)}'
                    })
            
            current_date += timedelta(days=1)
        
        return {
            'available': len(conflicts) == 0,
            'conflicts': conflicts
        }
