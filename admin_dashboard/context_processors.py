from users.models import Skill
from reports.models import Report
from admin_dashboard.models import FlaggedChat
from services.models import ServicePost
from notifications.models import Notification

def admin_notifications(request):
    """
    Context processor to add pending counts to all admin dashboard templates
    """
    if request.user.is_authenticated and request.user.role == 'admin':
        return {
            'pending_skills_count': Skill.objects.filter(status='pending').count(),
            'pending_reports_count': Report.objects.filter(status='pending').count(),
            'pending_flagged_chats_count': FlaggedChat.objects.filter(status='pending').count(),
            'pending_services_count': ServicePost.objects.filter(status='pending').count(),
            'unread_notifications_count': Notification.objects.filter(user=request.user, is_read=False, is_archived=False).count(),
        }
    return {
        'pending_skills_count': 0,
        'pending_reports_count': 0,
        'pending_flagged_chats_count': 0,
        'pending_services_count': 0,
        'unread_notifications_count': 0,
    }
