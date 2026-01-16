"""
Views for interview scheduling and management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta

from .models import JobApplication, InterviewSchedule, Contract
from .utils_interview import (
    generate_jitsi_room, 
    create_calendar_event, 
    get_interview_time_display,
    get_workflow_step_info,
    calculate_progress_percentage
)
from notifications.models import Notification


@login_required
@require_POST
def schedule_interview(request, application_pk):
    """Employer schedules an interview for an application"""
    application = get_object_or_404(JobApplication, pk=application_pk)
    
    # Check permission: only job owner can schedule
    if request.user != application.job.owner:
        messages.error(request, "You don't have permission to schedule interviews for this job.")
        return redirect('jobs:job_detail', id=application.job.id)
    
    # Get form data
    scheduled_date = request.POST.get('scheduled_date')
    scheduled_time = request.POST.get('scheduled_time')
    duration_minutes = int(request.POST.get('duration_minutes', 30))
    interview_type = request.POST.get('interview_type', 'video')
    meeting_notes = request.POST.get('meeting_notes', '')
    phone_number = request.POST.get('phone_number', '')
    location_address = request.POST.get('location_address', '')
    
    # Validate required fields
    if not scheduled_date or not scheduled_time:
        messages.error(request, "Please provide both date and time for the interview.")
        return redirect('jobs:application_detail', pk=application_pk)
    
    # Parse datetime
    try:
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        scheduled_datetime = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")
        scheduled_datetime = timezone.make_aware(scheduled_datetime)
        
        # Validate future date
        if scheduled_datetime <= timezone.now():
            messages.error(request, "Interview must be scheduled in the future.")
            return redirect('jobs:application_detail', pk=application_pk)
            
    except ValueError:
        messages.error(request, "Invalid date or time format.")
        return redirect('jobs:application_detail', pk=application_pk)
    
    # Check if interview already exists
    if hasattr(application, 'interview'):
        messages.warning(request, "An interview is already scheduled for this application.")
        return redirect('jobs:application_detail', pk=application_pk)
    
    # Generate video room if video interview
    video_room_id = ''
    video_room_url = ''
    if interview_type == 'video':
        jitsi_data = generate_jitsi_room(application)
        video_room_id = jitsi_data['room_id']
        video_room_url = jitsi_data['room_url']
    
    # Create interview schedule
    interview = InterviewSchedule.objects.create(
        application=application,
        scheduled_by=request.user,
        scheduled_datetime=scheduled_datetime,
        duration_minutes=duration_minutes,
        interview_type=interview_type,
        video_room_id=video_room_id,
        video_room_url=video_room_url,
        meeting_notes=meeting_notes,
        phone_number=phone_number,
        location_address=location_address,
        status='scheduled'
    )
    
    # Update application workflow
    application.workflow_status = 'interview_scheduled'
    application.current_step = 3
    application.is_shortlisted = True
    application.save()
    
    # Send notification to worker
    Notification.objects.create(
        user=application.worker,
        message=f"📅 Interview scheduled for '{application.job.title}' on {scheduled_datetime.strftime('%b %d, %Y at %I:%M %p')}",
        notif_type="interview",
        object_id=interview.pk
    )
    
    messages.success(request, f"Interview scheduled successfully for {scheduled_datetime.strftime('%b %d, %Y at %I:%M %p')}!")
    return redirect('jobs:application_detail', pk=application_pk)


@login_required
def join_interview(request, interview_pk):
    """Worker or employer joins video interview"""
    interview = get_object_or_404(InterviewSchedule, pk=interview_pk)
    application = interview.application
    
    # Check permission: only worker or employer can join
    if request.user not in [application.worker, application.job.owner]:
        messages.error(request, "You don't have permission to join this interview.")
        return redirect('mainpages:home')
    
    # Check if interview can be joined
    if not interview.can_join():
        messages.warning(request, "This interview is not available to join yet. Please wait until 5 minutes before the scheduled time.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # For video interviews, redirect to Jitsi room
    if interview.interview_type == 'video' and interview.video_room_url:
        return redirect(interview.video_room_url)
    
    # For other types, show details
    context = {
        'interview': interview,
        'application': application,
    }
    return render(request, 'jobs/interview_join.html', context)


@login_required
@require_POST
def complete_interview(request, interview_pk):
    """Mark interview as completed and add feedback"""
    interview = get_object_or_404(InterviewSchedule, pk=interview_pk)
    application = interview.application
    
    # Check permission: only employer can mark as completed
    if request.user != application.job.owner:
        messages.error(request, "Only the employer can mark the interview as completed.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Get feedback and rating
    interview_feedback = request.POST.get('interview_feedback', '')
    interview_rating = request.POST.get('interview_rating', None)
    
    if interview_rating:
        try:
            interview_rating = int(interview_rating)
            if interview_rating < 1 or interview_rating > 5:
                interview_rating = None
        except (ValueError, TypeError):
            interview_rating = None
    
    # Mark as completed
    interview.mark_completed(feedback=interview_feedback, rating=interview_rating)
    
    # Notify worker
    Notification.objects.create(
        user=application.worker,
        message=f"✅ Interview for '{application.job.title}' has been marked as completed. The employer will review and get back to you.",
        notif_type="interview",
        object_id=interview.pk
    )
    
    messages.success(request, "Interview marked as completed successfully!")
    return redirect('jobs:application_detail', pk=application.pk)


@login_required
@require_POST
def reschedule_interview(request, interview_pk):
    """Reschedule an existing interview"""
    interview = get_object_or_404(InterviewSchedule, pk=interview_pk)
    application = interview.application
    
    # Check permission: only employer can reschedule
    if request.user != application.job.owner:
        messages.error(request, "Only the employer can reschedule interviews.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Get new date/time
    scheduled_date = request.POST.get('scheduled_date')
    scheduled_time = request.POST.get('scheduled_time')
    
    if not scheduled_date or not scheduled_time:
        messages.error(request, "Please provide both date and time.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Parse datetime
    try:
        scheduled_datetime_str = f"{scheduled_date} {scheduled_time}"
        scheduled_datetime = datetime.strptime(scheduled_datetime_str, "%Y-%m-%d %H:%M")
        scheduled_datetime = timezone.make_aware(scheduled_datetime)
        
        if scheduled_datetime <= timezone.now():
            messages.error(request, "Interview must be scheduled in the future.")
            return redirect('jobs:application_detail', pk=application.pk)
            
    except ValueError:
        messages.error(request, "Invalid date or time format.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Update interview
    interview.scheduled_datetime = scheduled_datetime
    interview.status = 'rescheduled'
    interview.save()
    
    # Notify worker
    Notification.objects.create(
        user=application.worker,
        message=f"📅 Interview for '{application.job.title}' has been rescheduled to {scheduled_datetime.strftime('%b %d, %Y at %I:%M %p')}",
        notif_type="interview",
        object_id=interview.pk
    )
    
    messages.success(request, "Interview rescheduled successfully!")
    return redirect('jobs:application_detail', pk=application.pk)


@login_required
@require_POST
def cancel_interview(request, interview_pk):
    """Cancel an interview"""
    interview = get_object_or_404(InterviewSchedule, pk=interview_pk)
    application = interview.application
    
    # Check permission: only employer can cancel
    if request.user != application.job.owner:
        messages.error(request, "Only the employer can cancel interviews.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Cancel interview
    interview.cancel()
    
    # Update application workflow back to under review
    application.workflow_status = 'under_review'
    application.current_step = 2
    application.save()
    
    # Notify worker
    Notification.objects.create(
        user=application.worker,
        message=f"❌ Interview for '{application.job.title}' has been cancelled.",
        notif_type="interview",
        object_id=interview.pk
    )
    
    messages.success(request, "Interview cancelled successfully.")
    return redirect('jobs:application_detail', pk=application.pk)


@login_required
def download_interview_calendar(request, interview_pk):
    """Download .ics calendar file for interview"""
    interview = get_object_or_404(InterviewSchedule, pk=interview_pk)
    application = interview.application
    
    # Check permission
    if request.user not in [application.worker, application.job.owner]:
        messages.error(request, "You don't have permission to access this interview.")
        return redirect('mainpages:home')
    
    # Generate calendar file
    ical_data = create_calendar_event(interview)
    
    if not ical_data:
        messages.error(request, "Calendar file generation is not available.")
        return redirect('jobs:application_detail', pk=application.pk)
    
    # Return as downloadable file
    response = HttpResponse(ical_data, content_type='text/calendar')
    filename = f"interview_{application.job.title.replace(' ', '_')}_{interview.scheduled_datetime.strftime('%Y%m%d')}.ics"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@login_required
def hiring_workflow_view(request, application_pk):
    """Display step-by-step hiring workflow for an application"""
    application = get_object_or_404(JobApplication, pk=application_pk)
    
    # Check permission
    if request.user not in [application.worker, application.job.owner]:
        messages.error(request, "You don't have permission to view this application.")
        return redirect('mainpages:home')
    
    # Get workflow info
    workflow_info = get_workflow_step_info(application.workflow_status)
    progress_percentage = calculate_progress_percentage(application.current_step)
    
    # Get interview if exists
    interview = None
    if hasattr(application, 'interview'):
        interview = application.interview
    
    # Get contract if exists
    contract = application.current_contract
    
    context = {
        'application': application,
        'workflow_info': workflow_info,
        'progress_percentage': progress_percentage,
        'current_step': application.current_step,
        'total_steps': 8,
        'interview': interview,
        'contract': contract,
        'is_worker': request.user == application.worker,
        'is_employer': request.user == application.job.owner,
    }
    
    return render(request, 'jobs/hiring_workflow.html', context)
