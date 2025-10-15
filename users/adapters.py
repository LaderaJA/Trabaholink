from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter for handling regular signups.
    """
    
    def save_user(self, request, user, form, commit=True):
        """
        Save user with CustomUser model fields.
        """
        user = super().save_user(request, user, form, commit=False)
        
        # Ensure role is set
        if hasattr(form, 'cleaned_data') and 'role' in form.cleaned_data:
            user.role = form.cleaned_data.get('role', 'client')
        elif not user.role:
            user.role = 'client'
        
        if commit:
            user.save()
        
        return user


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter to handle social account signup.
    Ensures that users created via social auth have proper defaults for CustomUser model.
    """
    
    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        Connect to existing user if email matches.
        """
        # If the user is already logged in, do nothing
        if sociallogin.is_existing:
            return
        
        # Try to connect social account to existing user with same email
        try:
            email = sociallogin.account.extra_data.get('email', '').lower()
            if email:
                # Check if user exists with this email
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    # Connect the social account to the existing user
                    sociallogin.connect(request, user)
        except Exception as e:
            # Log the error but don't fail the login
            print(f"Error in pre_social_login: {e}")
            pass
    
    def new_user(self, request, sociallogin):
        """
        Instantiate a new User instance for social signup.
        """
        user = super().new_user(request, sociallogin)
        
        # Set default values for CustomUser fields
        user.role = 'client'
        user.identity_verification_status = 'skipped'
        
        return user
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user information from social provider data.
        Handles CustomUser model fields properly.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Ensure role is set for new users
        if not user.pk:  # New user
            user.role = 'client'
            user.identity_verification_status = 'skipped'
        
        # Extract additional data from Google
        extra_data = sociallogin.account.extra_data
        
        # Set first and last name if available
        if 'given_name' in extra_data:
            user.first_name = extra_data.get('given_name', '')
        if 'family_name' in extra_data:
            user.last_name = extra_data.get('family_name', '')
        
        # Set email if not already set
        if not user.email and 'email' in extra_data:
            user.email = extra_data.get('email', '')
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after social signup.
        Ensures all CustomUser fields are properly set.
        """
        user = super().save_user(request, sociallogin, form)
        
        # Double-check CustomUser fields are set
        needs_save = False
        
        if not user.role:
            user.role = 'client'
            needs_save = True
        
        if user.identity_verification_status == 'pending':
            user.identity_verification_status = 'skipped'
            needs_save = True
        
        if needs_save:
            user.save()
        
        return user
    
    def get_login_redirect_url(self, request):
        """
        Redirect after successful social login.
        """
        # Use the LOGIN_REDIRECT_URL from settings
        return settings.LOGIN_REDIRECT_URL or '/'
