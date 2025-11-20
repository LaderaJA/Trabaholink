from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from users.models import CustomUser
from jobs.models import Job


@login_required
def search_users(request):
    """API endpoint to search for users by username or email"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    users = CustomUser.objects.filter(
        Q(username__icontains=query) | 
        Q(email__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query)
    ).exclude(
        id=request.user.id  # Exclude current user
    )[:10]  # Limit to 10 results
    
    results = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
        'is_active': user.is_active,
        'role': user.get_role_display()
    } for user in users]
    
    return JsonResponse({'results': results})


@login_required
def search_jobs(request):
    """API endpoint to search for job postings by title or ID"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Try to search by ID if query is numeric
    jobs_query = Q(title__icontains=query) | Q(description__icontains=query)
    if query.isdigit():
        jobs_query |= Q(id=int(query))
    
    jobs = Job.objects.filter(jobs_query).select_related('owner')[:10]
    
    results = [{
        'id': job.id,
        'title': job.title,
        'owner': job.owner.username,
        'is_active': job.is_active,
        'budget': str(job.budget),
        'created_at': job.created_at.strftime('%Y-%m-%d')
    } for job in jobs]
    
    return JsonResponse({'results': results})
