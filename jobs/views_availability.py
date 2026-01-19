"""
Worker Availability Management Views
Allows workers to set their available working hours per day of the week.
"""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from datetime import time as dt_time
import json

from .models import WorkerAvailability


@login_required
@require_http_methods(["GET", "POST"])
def manage_availability(request):
    """
    View for workers to manage their weekly availability schedule.
    GET: Display current availability settings
    POST: Save/update availability settings
    """
    # Allow both legacy flag (is_worker) and role-based check
    is_worker_flag = getattr(request.user, 'is_worker', False)
    is_worker_role = getattr(request.user, 'role', '') == 'worker'
    if not (is_worker_flag or is_worker_role):
        messages.error(request, "Only workers can manage availability schedules.")
        return redirect('users:profile', pk=request.user.pk)
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            availability_data = data.get('availability', [])
            
            # Clear existing availability for this worker
            WorkerAvailability.objects.filter(worker=request.user).delete()
            
            # Create new availability entries
            created_count = 0
            for entry in availability_data:
                day_of_week = entry.get('day_of_week')
                start_time = entry.get('start_time')
                end_time = entry.get('end_time')
                is_available = entry.get('is_available', True)
                
                if day_of_week is not None and start_time and end_time:
                    # Parse time strings (format: "HH:MM")
                    start_hour, start_min = map(int, start_time.split(':'))
                    end_hour, end_min = map(int, end_time.split(':'))
                    
                    WorkerAvailability.objects.create(
                        worker=request.user,
                        day_of_week=day_of_week,
                        start_time=dt_time(start_hour, start_min),
                        end_time=dt_time(end_hour, end_min),
                        is_available=is_available
                    )
                    created_count += 1
            
            return JsonResponse({
                'success': True,
                'message': f'Availability updated successfully! {created_count} time slots saved.',
                'count': created_count
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error saving availability: {str(e)}'
            }, status=400)
    
    # GET request - display current availability
    availability = WorkerAvailability.objects.filter(
        worker=request.user
    ).order_by('day_of_week', 'start_time')
    
    # Format availability for template
    availability_by_day = {}
    for item in availability:
        day = item.day_of_week
        if day not in availability_by_day:
            availability_by_day[day] = []
        availability_by_day[day].append({
            'id': item.id,
            'start_time': item.start_time.strftime('%H:%M'),
            'end_time': item.end_time.strftime('%H:%M'),
            'is_available': item.is_available
        })
    
    context = {
        'availability': availability,
        'availability_by_day': availability_by_day,
        'days_of_week': WorkerAvailability.DAYS_OF_WEEK,
    }
    
    return render(request, 'jobs/manage_availability.html', context)


@login_required
def get_availability_api(request):
    """
    API endpoint to get worker's availability schedule.
    Returns JSON format for calendar/schedule displays.
    """
    worker_id = request.GET.get('worker_id')
    
    if worker_id:
        # Get specific worker's availability (for employers viewing worker profile)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        worker = get_object_or_404(User, pk=worker_id, is_worker=True)
    else:
        # Get current user's availability
        if not request.user.is_worker:
            return JsonResponse({'error': 'User is not a worker'}, status=403)
        worker = request.user
    
    availability = WorkerAvailability.objects.filter(
        worker=worker,
        is_available=True
    ).order_by('day_of_week', 'start_time')
    
    # Format for JSON response
    availability_data = []
    for item in availability:
        availability_data.append({
            'day_of_week': item.day_of_week,
            'day_name': dict(WorkerAvailability.DAYS_OF_WEEK)[item.day_of_week],
            'start_time': item.start_time.strftime('%I:%M %p'),
            'end_time': item.end_time.strftime('%I:%M %p'),
            'start_time_24h': item.start_time.strftime('%H:%M'),
            'end_time_24h': item.end_time.strftime('%H:%M'),
        })
    
    return JsonResponse({
        'success': True,
        'worker_id': worker.id,
        'worker_name': worker.get_full_name() or worker.username,
        'availability': availability_data
    })


@login_required
def check_availability_conflicts(request):
    """
    Check if a proposed schedule conflicts with worker's availability.
    Used when creating job offers or contracts.
    """
    if request.method != "POST":
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        worker_id = data.get('worker_id')
        start_date = data.get('start_date')  # Format: YYYY-MM-DD
        end_date = data.get('end_date')
        start_time = data.get('start_time')  # Format: HH:MM
        end_time = data.get('end_time')
        
        from django.contrib.auth import get_user_model
        from datetime import datetime
        
        User = get_user_model()
        worker = get_object_or_404(User, pk=worker_id, is_worker=True)
        
        # Parse dates and times
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))
        start_time_obj = dt_time(start_hour, start_min)
        end_time_obj = dt_time(end_hour, end_min)
        
        # Check availability
        result = WorkerAvailability.check_availability_for_contract(
            worker=worker,
            start_date=start_date_obj,
            end_date=end_date_obj,
            start_time=start_time_obj,
            end_time=end_time_obj
        )
        
        return JsonResponse({
            'success': True,
            'available': result['available'],
            'conflicts': [
                {
                    'date': c['date'].strftime('%Y-%m-%d'),
                    'date_formatted': c['date'].strftime('%a, %b %d, %Y'),
                    'reason': c['reason']
                }
                for c in result['conflicts'][:10]  # Limit to 10 conflicts
            ],
            'total_conflicts': len(result['conflicts'])
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
