"""
Context processors for the users app.
Makes user guide status available globally in templates.
"""
from django.conf import settings


def user_guide_context(request):
    """
    Add user guide status to every template context.
    
    This makes guide status available globally without needing
    to pass it explicitly in every view.
    
    Template usage:
        {% if user_guide.auto_popup_enabled %}
            <!-- Show auto-popup -->
        {% endif %}
        
        {{ user_guide.last_page_viewed }}
        {{ user_guide.total_guides_viewed }}
    """
    context = {
        'user_guide': None,
        'user_guide_enabled': False,
    }
    
    # Only add guide status for authenticated users
    if request.user.is_authenticated:
        try:
            guide_status = request.user.guide_status
            context['user_guide'] = guide_status
            context['user_guide_enabled'] = True
        except Exception:
            # Handle case where guide_status doesn't exist
            # This shouldn't happen due to signals, but handle gracefully
            from users.models import UserGuideStatus
            guide_status, created = UserGuideStatus.objects.get_or_create(
                user=request.user,
                defaults={
                    'auto_popup_enabled': True,
                    'pages_completed': {},
                }
            )
            context['user_guide'] = guide_status
            context['user_guide_enabled'] = True
    
    return context
