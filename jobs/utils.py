from .models import Job, JobApplication

def get_users_who_applied(job_id):
    try:
        job = Job.objects.get(id=job_id)
        applications = JobApplication.objects.filter(job=job)
        users = [application.worker for application in applications]
        return users
    except Job.DoesNotExist:
        return []