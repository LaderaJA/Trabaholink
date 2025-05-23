from .models import Job, JobApplication

def get_users_who_applied(job_id):
    """
    Returns a list of users who applied for a specific job.

    Args:
        job_id (int): The ID of the job.

    Returns:
        list: A list of user objects who applied for the job.
    """
    try:
        job = Job.objects.get(id=job_id)
        applications = JobApplication.objects.filter(job=job)
        users = [application.worker for application in applications]
        return users
    except Job.DoesNotExist:
        return []