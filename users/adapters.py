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
        
        NOTE: We DON'T auto-connect here to allow new users to select their role.
        The signup form will be shown to all new Google sign-ins.
        """
        print("=" * 80)
        print("DEBUG: pre_social_login CALLED")
        print(f"DEBUG: is_existing = {sociallogin.is_existing}")
        print(f"DEBUG: user = {sociallogin.user}")
        print(f"DEBUG: user.pk = {sociallogin.user.pk if sociallogin.user else None}")
        
        # If the account already exists in our database, user will login directly
        if sociallogin.is_existing:
            print(f"DEBUG: *** SOCIAL ACCOUNT EXISTS - LOGGING IN DIRECTLY (SKIPPING FORM) ***")
            return
        
        # Log the email for debugging
        try:
            email = sociallogin.account.extra_data.get('email', '').lower()
            print(f"DEBUG: Email from Google: {email}")
            
            # Check if a regular user exists with this email
            user = User.objects.filter(email__iexact=email).first()
            if user:
                print(f"DEBUG: *** Regular user exists with this email ***")
                print(f"DEBUG: User ID: {user.pk}, Username: {user.username}, Role: {user.role}")
                print(f"DEBUG: NOT auto-connecting - will show signup form")
            else:
                print(f"DEBUG: *** NO user exists - will show signup form ***")
        except Exception as e:
            print(f"Error in pre_social_login: {e}")
        
        print("=" * 80)
    
    def new_user(self, request, sociallogin):
        """
        Instantiate a new User instance for social signup.
        """
        user = super().new_user(request, sociallogin)
        
        # Set default values for all CustomUser fields
        user.role = 'client'  # Default role (will be changed in role selection)
        user.role_selected = False  # ✅ IMPORTANT: Mark that role hasn't been selected yet
        user.identity_verification_status = 'skipped'
        user.verification_status = 'pending'
        user.face_detected = False
        user.ocr_confidence_score = 0
        user.is_verified = False
        user.is_verified_philsys = False
        
        return user
    
    def populate_user(self, request, sociallogin, data):
        """
        Populate user information from social provider data.
        Handles CustomUser model fields properly.
        """
        # Extract email from data FIRST before calling super
        extra_data = sociallogin.account.extra_data
        email = extra_data.get('email', data.get('email', ''))
        
        # Ensure email is in data dict for super() to use
        if email and 'email' not in data:
            data['email'] = email
        
        user = super().populate_user(request, sociallogin, data)
        
        # CRITICAL: Ensure email is set
        if not user.email and email:
            user.email = email
        
        # Ensure all fields are set for new users
        if not user.pk:  # New user
            user.role = 'client'  # Temporary default
            user.role_selected = False  # ✅ Must select role
            user.identity_verification_status = 'skipped'
            user.verification_status = 'pending'
            user.face_detected = False
            user.ocr_confidence_score = 0
            user.is_verified = False
            user.is_verified_philsys = False
        
        # Set first and last name if available
        if 'given_name' in extra_data:
            user.first_name = extra_data.get('given_name', '')
        if 'family_name' in extra_data:
            user.last_name = extra_data.get('family_name', '')
        
        return user
    
    def save_user(self, request, sociallogin, form=None):
        """
        Save the user after social signup.
        Ensures all CustomUser fields are properly set and saves role from form.
        """
        # Extract data from social account
        extra_data = sociallogin.account.extra_data
        email = extra_data.get('email')
        print(f"DEBUG: Email from social account: {email}")
        
        # Get the user from sociallogin
        user = sociallogin.user
        
        # Ensure email is set
        if not user.email and email:
            user.email = email
            print(f"DEBUG: Set email to user: {user.email}")
        
        # Generate username if not set
        if not user.username:
            # Try to use email username part
            if email:
                base_username = email.split('@')[0]
            else:
                # Fallback to name
                base_username = extra_data.get('given_name', 'user').lower()
            
            # Make username unique
            username = base_username
            counter = 1
            from django.contrib.auth import get_user_model
            User = get_user_model()
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user.username = username
            print(f"DEBUG: Generated username: {user.username}")
        
        # Get role from form if provided
        if form and hasattr(form, 'cleaned_data'):
            role = form.cleaned_data.get('role', None)
            if role:
                user.role = role
                print(f"DEBUG: Set role from form: {user.role}")
        
        # Ensure all required fields are set
        if not user.role:
            user.role = 'client'
        
        if user.identity_verification_status == 'pending':
            user.identity_verification_status = 'skipped'
        
        # Save the user with all fields set
        print(f"DEBUG: Saving user - username: {user.username}, email: {user.email}, role: {user.role}")
        print(f"DEBUG: role_selected = {user.role_selected}")
        
        # Check if this is a new user BEFORE saving
        is_new = not user.pk
        print(f"DEBUG: is_new = {is_new}")
        
        user.save()
        print(f"DEBUG: User saved with PK = {user.pk}")
        print(f"DEBUG: role_selected after save = {user.role_selected}")
        
        # Set session flag for new users to redirect to role selection
        if is_new:
            request.session['needs_role_selection'] = True
            request.session.modified = True  # Force session save
            print(f"DEBUG: *** SET needs_role_selection = True ***")
            print(f"DEBUG: Session data: {dict(request.session)}")
        
        # Complete the social login connection
        sociallogin.save(request)
        
        return user
    
    def get_login_redirect_url(self, request):
        """
        Redirect after successful social login.
        For new social users, redirect to role selection page.
        For existing users, redirect to their profile.
        """
        print("=" * 80)
        print("DEBUG: get_login_redirect_url CALLED")
        print(f"DEBUG: User: {request.user}")
        print(f"DEBUG: User ID: {request.user.pk}")
        print(f"DEBUG: User email: {request.user.email}")
        print(f"DEBUG: User role: {request.user.role}")
        print(f"DEBUG: Session keys: {list(request.session.keys())}")
        print(f"DEBUG: needs_role_selection = {request.session.get('needs_role_selection', 'NOT SET')}")
        
        user = request.user
        
        # Check if user needs to select role
        # Use database field instead of session for reliability
        print(f"DEBUG: user.role_selected = {user.role_selected}")
        print(f"DEBUG: user.date_joined = {user.date_joined}")
        
        # FORCE role selection for users without role_selected set
        if not user.role_selected:
            needs_selection = True
            print(f"DEBUG: ❌ role_selected is FALSE - MUST show role selection")
        else:
            needs_selection = False
            print(f"DEBUG: ✅ role_selected is TRUE - skip to profile")
        
        print(f"DEBUG: FINAL needs_selection = {needs_selection}")
        
        if needs_selection:
            print(f"DEBUG: *** USER HASN'T SELECTED ROLE - REDIRECTING TO ROLE SELECTION ***")
            print("=" * 80)
            return '/users/select-role/'
        
        # Existing user - go to profile
        print(f"DEBUG: *** REDIRECTING TO HOME/PROFILE ***")
        print("=" * 80)
        return settings.LOGIN_REDIRECT_URL or '/'
    
    def authentication_error(self, request, provider_id, error=None, exception=None, extra_context=None):
        """
        Handle authentication errors including cancellations.
        Redirect to register page instead of showing bare error page.
        """
        # Redirect to register page on cancellation or error
        from django.shortcuts import redirect
        from django.contrib import messages
        
        messages.warning(request, 'Social login was cancelled. Please try again or register manually.')
        return redirect('/users/register/')
