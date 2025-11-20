from jobs.models import Job, JobApplication


def user_dashboard_access(request):
    """
    Context processor to determine which dashboards the user can access
    based on their activity (job postings and applications)
    """
    context = {
        'has_job_postings': False,
        'has_job_applications': False,
    }
    
    if request.user.is_authenticated:
        # Check if user has posted any jobs (employer dashboard access)
        context['has_job_postings'] = Job.objects.filter(owner=request.user).exists()
        
        # Check if user has applied to any jobs (worker dashboard access)
        context['has_job_applications'] = JobApplication.objects.filter(worker=request.user).exists()
    
    return context
