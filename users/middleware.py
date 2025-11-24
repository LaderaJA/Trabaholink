from django.shortcuts import redirect
from django.urls import reverse


class NoCacheMiddleware:
    """
    Middleware to prevent caching of all pages (authenticated or not).
    This prevents the back button from showing cached authenticated content after logout.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add no-cache headers to all pages to prevent back button issues
        # This is especially important for authenticated pages and logout
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        
        return response


class RoleSelectionMiddleware:
    """
    Middleware to redirect users who haven't selected their role yet.
    This catches Google OAuth users after they sign up.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Skip if already on role selection page or logout
        if request.path in ['/users/select-role/', '/users/logout/', '/accounts/logout/']:
            return self.get_response(request)
        
        # Skip for admin users
        if request.user.is_staff or request.user.is_superuser:
            return self.get_response(request)
        
        # Check if user needs to select role
        if not request.user.role_selected:
            print(f"🔴 MIDDLEWARE: User {request.user.username} needs role selection - redirecting!")
            return redirect('/users/select-role/')
        
        # Continue normally
        return self.get_response(request)
