"""
Middleware to redirect new users to complete their profile setup.
"""
from django.shortcuts import redirect
from django.urls import reverse


class ProfileSetupMiddleware:
    """
    Redirects newly registered users to complete their profile setup.
    Users can skip this step if they want.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URL prefixes that don't require profile completion
        self.exempt_url_prefixes = [
            '/users/profile/',
            '/users/logout/',
            '/users/change-password/',
            '/users/skip-profile-setup/',
            '/users/select-role/',  # Allow role selection before profile setup
            '/users/guide/',  # User guide API endpoints must be accessible during onboarding
            '/static/',
            '/media/',
            '/admin/',
            '/accounts/logout/',
            '/accounts/login/',
            '/users/login/',
            '/users/register/',
        ]
    
    def __call__(self, request):
        # Check if user is authenticated and hasn't completed profile
        if request.user.is_authenticated and not request.user.profile_completed:
            # Check if current URL is exempt
            current_path = request.path
            is_exempt = any(current_path.startswith(prefix) for prefix in self.exempt_url_prefixes)
            
            if not is_exempt:
                # Redirect to user's profile edit page with onboarding flag
                profile_edit_url = reverse('users:profile_edit', kwargs={'pk': request.user.pk})
                return redirect(f"{profile_edit_url}?onboarding=true")
        
        response = self.get_response(request)
        return response
