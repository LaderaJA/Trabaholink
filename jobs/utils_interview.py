"""
Utility functions for interview scheduling and video conferencing
"""
import uuid
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def generate_daily_room(application):
    """
    Generate Daily.co video room for interview
    
    Args:
        application: JobApplication instance
    
    Returns:
        dict with room_name, room_url
    """
    import requests
    from django.conf import settings
    
    # Get API key from settings
    api_key = getattr(settings, 'DAILY_API_KEY', '49faac40d7730a5b418232f9206c7439f1b503e8bca746d76699aa1e3c4906fa')
    
    # Create unique room name
    room_name = f"trabaholink-interview-{application.pk}-{uuid.uuid4().hex[:8]}"
    
    try:
        # Call Daily.co REST API to create room
        response = requests.post(
            'https://api.daily.co/v1/rooms',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'name': room_name,
                'privacy': 'public',
                'properties': {
                    'enable_screenshare': True,
                    'enable_chat': True,
                    'enable_knocking': False,
                    'enable_prejoin_ui': True,
                    'exp': int(timezone.now().timestamp()) + (7 * 24 * 60 * 60),
                }
            },
            timeout=10
        )
        
        if response.status_code == 200:
            room = response.json()
            room_url = room['url']
        else:
            raise Exception(f"API returned status {response.status_code}: {response.text}")
        
    except Exception as e:
        # Fallback: create room URL without API (works for demo)
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f'Daily.co API error: {e}. Using domain URL.')
        room_url = f"https://trabaholink.daily.co/{room_name}"
    
    return {
        'room_name': room_name,
        'room_url': room_url,
    }


# Keep old function name for backwards compatibility
def generate_jitsi_room(application):
    """Deprecated: Use generate_daily_room instead"""
    return generate_daily_room(application)


def create_calendar_event(interview):
    """
    Generate .ics calendar file for interview
    
    Args:
        interview: InterviewSchedule instance
    
    Returns:
        icalendar data as bytes
    """
    try:
        from icalendar import Calendar, Event
    except ImportError:
        # If icalendar is not installed, return None
        return None
    
    cal = Calendar()
    cal.add('prodid', '-//TrabahoLink Interview//trabaholink.com//')
    cal.add('version', '2.0')
    
    event = Event()
    event.add('summary', f'Interview: {interview.application.job.title}')
    event.add('dtstart', interview.scheduled_datetime)
    event.add('dtend', interview.scheduled_datetime + timedelta(minutes=interview.duration_minutes))
    
    # Description with interview details
    description = f"""
Interview for: {interview.application.job.title}
Company: {interview.application.job.owner.get_full_name() or interview.application.job.owner.username}
Candidate: {interview.application.worker.get_full_name() or interview.application.worker.username}

Interview Type: {interview.get_interview_type_display()}
"""
    
    if interview.interview_type == 'video':
        description += f"\nVideo Call Link: {interview.video_room_url}\n"
        event.add('location', interview.video_room_url)
    elif interview.interview_type == 'phone':
        description += f"\nPhone Number: {interview.phone_number}\n"
        event.add('location', f"Phone: {interview.phone_number}")
    elif interview.interview_type == 'in_person':
        description += f"\nLocation: {interview.location_address}\n"
        event.add('location', interview.location_address)
    
    if interview.meeting_notes:
        description += f"\nNotes: {interview.meeting_notes}"
    
    event.add('description', description.strip())
    
    # Add reminder (15 minutes before)
    from icalendar import Alarm
    alarm = Alarm()
    alarm.add('action', 'DISPLAY')
    alarm.add('trigger', timedelta(minutes=-15))
    alarm.add('description', 'Interview reminder')
    event.add_component(alarm)
    
    cal.add_component(event)
    
    return cal.to_ical()


def get_interview_time_display(interview):
    """
    Get human-friendly time display for interview
    
    Args:
        interview: InterviewSchedule instance
    
    Returns:
        str: Formatted time string
    """
    now = timezone.now()
    delta = interview.scheduled_datetime - now
    
    if delta.total_seconds() < 0:
        # Past interview
        delta = now - interview.scheduled_datetime
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds < 3600:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        # Upcoming interview
        if delta.days > 0:
            return f"in {delta.days} day{'s' if delta.days > 1 else ''}"
        elif delta.seconds < 3600:
            minutes = delta.seconds // 60
            if minutes < 5:
                return "starting soon!"
            return f"in {minutes} minute{'s' if minutes > 1 else ''}"
        else:
            hours = delta.seconds // 3600
            return f"in {hours} hour{'s' if hours > 1 else ''}"


def get_workflow_step_info(workflow_status):
    """
    Get step number and display info for workflow status
    
    Args:
        workflow_status: Current workflow status string
    
    Returns:
        dict with step number, title, description
    """
    workflow_steps = {
        'submitted': {
            'step': 1,
            'title': 'Application Submitted',
            'description': 'Your application has been submitted and is awaiting review',
            'icon': '📝'
        },
        'under_review': {
            'step': 2,
            'title': 'Under Review',
            'description': 'Employer is reviewing your application',
            'icon': '👀'
        },
        'shortlisted': {
            'step': 3,
            'title': 'Shortlisted',
            'description': 'You have been shortlisted for an interview',
            'icon': '⭐'
        },
        'interview_scheduled': {
            'step': 3,
            'title': 'Interview Scheduled',
            'description': 'Your interview has been scheduled',
            'icon': '📅'
        },
        'interviewed': {
            'step': 4,
            'title': 'Interview Completed',
            'description': 'Interview completed, waiting for employer decision',
            'icon': '✅'
        },
        'offer_pending': {
            'step': 5,
            'title': 'Offer Pending',
            'description': 'Employer is preparing an offer',
            'icon': '📋'
        },
        'contract_sent': {
            'step': 6,
            'title': 'Contract Sent',
            'description': 'Employment contract has been sent for your review',
            'icon': '📄'
        },
        'contract_negotiation': {
            'step': 6,
            'title': 'Contract Negotiation',
            'description': 'Contract terms are being negotiated',
            'icon': '💬'
        },
        'hired': {
            'step': 7,
            'title': 'Hired',
            'description': 'Congratulations! You have been hired',
            'icon': '🎉'
        },
        'rejected': {
            'step': 0,
            'title': 'Application Rejected',
            'description': 'Your application was not successful this time',
            'icon': '❌'
        },
        'withdrawn': {
            'step': 0,
            'title': 'Application Withdrawn',
            'description': 'You have withdrawn your application',
            'icon': '🚫'
        }
    }
    
    return workflow_steps.get(workflow_status, workflow_steps['submitted'])


def calculate_progress_percentage(current_step, total_steps=8):
    """
    Calculate progress percentage for workflow
    
    Args:
        current_step: Current step number (1-8)
        total_steps: Total number of steps (default: 8)
    
    Returns:
        float: Progress percentage (0-100)
    """
    if current_step <= 0:
        return 0
    return min(100, (current_step / total_steps) * 100)
