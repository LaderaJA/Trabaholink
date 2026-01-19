from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash, get_backends
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView, DeleteView, FormView
from django.forms import inlineformset_factory, DateInput
from django.conf import settings
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied, SuspiciousFileOperation
from utils_gis import GEOSGeometry, USE_GIS
from django.http import JsonResponse
from django.db import models
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import File
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import uuid
import os
import json
import logging

from .models import (
    CustomUser,
    Skill,
    Education,
    Experience,
    CompletedJobGallery,
    AccountVerification,
    VALID_ID_CHOICES,
)
from users.services.verification import VerificationPipeline
from .forms import (CustomUserRegistrationForm, IdentityVerificationForm, UserProfileForm, 
                   SkillVerificationForm, CompletedJobGalleryForm, UserLocationForm,
                   VerificationStep1Form, VerificationStep2Form, VerificationStep3Form,
                   CustomPasswordResetForm)
from jobs.models import JobApplication, Contract, Feedback
from notifications.models import Notification

logger = logging.getLogger(__name__)

# Formsets for education and experience
# Custom base class to order education by highest to lowest (most recent first)
BaseEducationFormSet = inlineformset_factory(
    CustomUser,
    Education,
    fields=('title', 'degree', 'institution', 'start_year', 'end_year', 'description', 'order'),
    extra=1,
    can_delete=True,
    widgets={
        'title': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': "e.g. Bachelor's Degree, High School Diploma"
        }),
        'degree': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g. Bachelor of Science in Computer Science'
        }),
        'institution': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter the institution name'
        }),
        'start_year': forms.Select(attrs={
            'class': 'form-control',
        }),
        'end_year': forms.Select(attrs={
            'class': 'form-control',
        }),
        'description': forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Additional details about your studies'
        }),
        'order': forms.HiddenInput(attrs={
            'class': 'education-order-field'
        }),
    }
)

# Override to order education entries by year DESC (highest/most recent first)
class EducationFormSet(BaseEducationFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate year choices from current year down to 1950, plus "Present"
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(year), str(year)) for year in range(current_year, 1949, -1)]
        year_choices_with_present = [('Present', 'Present (Currently Studying)')] + year_choices
        
        # Apply year choices to all forms in the formset
        for form in self.forms:
            if 'start_year' in form.fields:
                form.fields['start_year'].widget = forms.Select(
                    choices=[('', 'Select Year')] + year_choices,
                    attrs={'class': 'form-control'}
                )
            if 'end_year' in form.fields:
                form.fields['end_year'].widget = forms.Select(
                    choices=[('', 'Select Year')] + year_choices_with_present,
                    attrs={'class': 'form-control'}
                )
    
    def get_queryset(self):
        qs = super().get_queryset()
        # Order by manual order field first, then by end year
        return qs.order_by('order', '-end_year', '-start_year')

BaseExperienceFormSet = inlineformset_factory(
    CustomUser,
    Experience,
    fields=('title', 'job_title', 'company', 'start_year', 'end_year', 'description', 'order'),
    extra=1,
    can_delete=True,
    widgets={
        'title': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': "e.g. Senior Developer Role, First Job"
        }),
        'job_title': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g. Software Engineer'
        }),
        'company': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter the company name'
        }),
        'start_year': forms.Select(attrs={
            'class': 'form-control',
        }),
        'end_year': forms.Select(attrs={
            'class': 'form-control',
        }),
        'description': forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Describe your role and responsibilities'
        }),
        'order': forms.HiddenInput(attrs={
            'class': 'experience-order-field'
        }),
    }
)

class ExperienceFormSet(BaseExperienceFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Generate year choices from current year down to 1950, plus "Present"
        from datetime import datetime
        current_year = datetime.now().year
        year_choices = [(str(year), str(year)) for year in range(current_year, 1949, -1)]
        year_choices_with_present = [('Present', 'Present (Currently Working)')] + year_choices
        
        # Apply year choices to all forms in the formset
        for form in self.forms:
            if 'start_year' in form.fields:
                form.fields['start_year'].widget = forms.Select(
                    choices=[('', 'Select Year')] + year_choices,
                    attrs={'class': 'form-control'}
                )
            if 'end_year' in form.fields:
                form.fields['end_year'].widget = forms.Select(
                    choices=[('', 'Select Year')] + year_choices_with_present,
                    attrs={'class': 'form-control'}
                )
    
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('order', '-end_year', '-start_year')

# Register View - Now with Email OTP Verification
class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = CustomUserRegistrationForm

    def form_valid(self, form):
        from django.contrib.auth.hashers import make_password
        from .otp_utils import create_otp_record, send_otp_email
        
        # Don't save the user yet - store data in OTP record
        email = form.cleaned_data['email']
        username = form.cleaned_data['username']
        password = form.cleaned_data['password1']
        role = form.cleaned_data.get('role', 'client')
        
        # Check if email or username already exists
        if CustomUser.objects.filter(email=email).exists():
            messages.error(self.request, 'An account with this email already exists.')
            return self.form_invalid(form)
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(self.request, 'This username is already taken.')
            return self.form_invalid(form)
        
        # Hash the password
        password_hash = make_password(password)
        
        # Create OTP record (returns record with _plain_otp attribute)
        otp_record = create_otp_record(email, username, password_hash, role)
        
        # Send OTP email using plain text OTP (not the hashed version)
        if send_otp_email(email, otp_record._plain_otp, username):
            messages.success(
                self.request, 
                f'A verification code has been sent to {email}. Please check your inbox.'
            )
            # Redirect to OTP verification page
            return redirect('verify_otp', email=email)
        else:
            messages.error(
                self.request, 
                'Failed to send verification email. Please try again.'
            )
            return self.form_invalid(form)

# Login View
class UserLoginView(LoginView):
    template_name = "users/login.html"
    
    def dispatch(self, request, *args, **kwargs):
        # If user is already authenticated, redirect to home
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        
        response = super().dispatch(request, *args, **kwargs)
        
        # Prevent caching of login page
        if hasattr(response, '__setitem__'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
    
    def get_success_url(self):
        """Redirect admins to dashboard, regular users to home"""
        user = self.request.user
        
        # Check if user is admin (staff or superuser)
        if user.is_staff or user.is_superuser:
            return reverse_lazy('admin_dashboard:dashboard_main')
        
        # Regular users go to jobs home
        return reverse_lazy('jobs:home')

# Logout View
class UserLogoutView(LogoutView):
    template_name = "users/logout.html"
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        # Prevent caching to avoid back button login issue
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response

class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy('password_reset_done')
    form_class = CustomPasswordResetForm

    def form_valid(self, form):
        try:
            email = form.cleaned_data.get('email', '')
            logger.info("Password reset requested for email: %s", email)
            print(f"[PWD RESET] request email={email}")
            return super().form_valid(form)
        except Exception as e:
            logger.error("Password reset email sending failed for %s: %s", email, str(e))
            print(f"[PWD RESET] error sending email for {email}: {e}")
            messages.error(self.request, 'We could not send the reset email. Please try again later.')
            return super().form_invalid(form)

    def form_invalid(self, form):
        logger.warning("Password reset form invalid: %s", form.errors)
        print(f"[PWD RESET] invalid form errors={form.errors}")
        messages.error(self.request, 'Please check the email and try again.')
        return super().form_invalid(form)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"

    def get(self, request, *args, **kwargs):
        logger.info("Password reset email dispatched.")
        print("[PWD RESET] done view")
        return super().get(request, *args, **kwargs)


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy('password_reset_complete')

    def dispatch(self, request, *args, **kwargs):
        uidb64 = kwargs.get('uidb64', '')
        token = kwargs.get('token', '')
        logger.info("Password reset confirm attempt uid prefix=%s token prefix=%s", uidb64[:6], token[:8])
        print(f"[PWD RESET] confirm attempt uid={uidb64[:6]} token={token[:8]}")
        try:
            response = super().dispatch(request, *args, **kwargs)
            return response
        except Exception as e:
            logger.error("Error during password reset confirm for uid=%s: %s", uidb64[:6], str(e))
            print(f"[PWD RESET] confirm error uid={uidb64[:6]} err={e}")
            messages.error(request, 'There was a problem validating the reset link.')
            return redirect('users:password_reset')

    def form_valid(self, form):
        try:
            resp = super().form_valid(form)
            logger.info("Password successfully reset.")
            print("[PWD RESET] password changed successfully")
            return resp
        except Exception as e:
            logger.error("Error saving new password: %s", str(e))
            print(f"[PWD RESET] error saving new password: {e}")
            messages.error(self.request, 'We could not set your new password. Please try again.')
            return super().form_invalid(form)

    def form_invalid(self, form):
        logger.warning("Password reset confirm form invalid: %s", form.errors)
        print(f"[PWD RESET] confirm invalid errors={form.errors}")
        messages.error(self.request, 'Please fix the errors and try again.')
        return super().form_invalid(form)


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"

    def get(self, request, *args, **kwargs):
        logger.info("Password reset completed.")
        print("[PWD RESET] complete view")
        return super().get(request, *args, **kwargs)

# Change Password View
@method_decorator(login_required, name='dispatch')
class ChangePasswordView(FormView):
    template_name = "users/change_password.html"
    form_class = PasswordChangeForm
    success_url = reverse_lazy('profile_edit')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        if self.request.method == 'POST':
            kwargs['data'] = self.request.POST
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)  # Important to keep the user logged in
        messages.success(self.request, 'Your password was successfully updated!')
        return super().form_valid(form)
        
    def get_success_url(self):
        return reverse('users:profile_edit', kwargs={'pk': self.request.user.pk})

# Privacy Settings View
@method_decorator(login_required, name='dispatch')
class PrivacySettingsView(UpdateView):
    from .models import PrivacySettings
    model = PrivacySettings
    template_name = "users/privacy_settings.html"
    fields = ['profile_visibility', 'show_email', 'show_phone', 'show_activity', 'allow_search_engines']
    success_url = reverse_lazy('users:privacy_settings')  # Fallback success URL

    def get_object(self):
        """Get or create privacy settings for the current user"""
        from .models import PrivacySettings
        settings, created = PrivacySettings.objects.get_or_create(user=self.request.user)
        return settings

    def get_success_url(self):
        messages.success(self.request, 'Your privacy settings have been updated successfully!')
        return reverse_lazy('users:privacy_settings')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context

# Profile Detail View
@method_decorator(login_required, name='dispatch')
class UserProfileDetailView(DetailView):
    model = CustomUser
    template_name = "users/profile_detail.html"
    context_object_name = "user"

    def get_object(self):
        return get_object_or_404(CustomUser, pk=self.kwargs['pk'])
    
    def dispatch(self, request, *args, **kwargs):
        """Check privacy settings before allowing access"""
        profile_user = self.get_object()
        current_user = request.user
        
        # Owner can always view their own profile
        if profile_user == current_user:
            return super().dispatch(request, *args, **kwargs)
        
        # Admin/staff can view all profiles
        if current_user.is_staff or current_user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
        
        # Check privacy settings
        try:
            from .models import PrivacySettings
            privacy_settings = PrivacySettings.objects.filter(user=profile_user).first()
            
            if privacy_settings:
                visibility = privacy_settings.profile_visibility
                
                if visibility == 'private':
                    # Private profile - only owner can view
                    messages.error(request, 'This profile is private and cannot be viewed.')
                    return redirect('jobs:home')
                
                elif visibility == 'connections':
                    # TODO: Check if users are connected (implement connections feature later)
                    # For now, treat as public
                    pass
            
            # If no privacy settings or visibility is public, allow access
            return super().dispatch(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error checking privacy settings: {e}")
            # On error, allow access (fail open for better UX)
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        current_user = self.request.user
        
        # Get privacy settings
        from .models import PrivacySettings
        privacy_settings = PrivacySettings.objects.filter(user=user).first()
        
        # Add privacy settings to context
        context['privacy_settings'] = privacy_settings
        context['can_view_email'] = privacy_settings.show_email if privacy_settings else True
        context['can_view_phone'] = privacy_settings.show_phone if privacy_settings else True
        context['is_own_profile'] = user == current_user
        
        # Determine user type
        context["is_worker"] = user.role == 'worker'
        context["is_client"] = user.role == 'client'
        
        # Get recent activity logs (last 20)
        from .activity_logger import ActivityLog
        context["recent_activities"] = ActivityLog.objects.filter(
            user=user
        ).select_related('content_type').order_by('-timestamp')[:20]
        
        # Worker-specific data
        if user.role == 'worker':
            context["recent_applications"] = JobApplication.objects.filter(worker=user).select_related("job").order_by("-applied_at")[:5]
            completed_contracts_qs = Contract.objects.filter(
                worker=user,
                status="Completed"
            ).select_related("job", "client").prefetch_related("feedbacks").order_by("-updated_at")

            feedback_map = {
                feedback.contract_id: feedback
                for feedback in Feedback.objects.filter(receiver=user).select_related("contract", "giver")
            }

            completed_contracts = list(completed_contracts_qs)
            for contract in completed_contracts:
                contract.worker_feedback = feedback_map.get(contract.id)

            context["completed_contracts"] = completed_contracts
            
            # Add user's services
            from services.models import ServicePost
            context["user_services"] = ServicePost.objects.filter(worker=user).order_by("-created_at")
        
        # Client-specific data
        if user.role == 'client':
            context["posted_jobs"] = user.posted_jobs.order_by("-created_at")
            
            # Count total pending applications across all jobs
            context["total_pending_applicants"] = JobApplication.objects.filter(
                job__owner=user,
                status='Pending'
            ).count()
            
            # Get completed contracts where user is the client, with worker feedback
            from django.db.models import Q
            completed_contracts_client = Contract.objects.filter(
                Q(client=user) | Q(job__owner=user),
                status="Completed"
            ).select_related("job", "worker", "client").prefetch_related("feedbacks").order_by("-updated_at")
            
            # Convert to list and attach worker feedback to each contract
            completed_contracts_list = list(completed_contracts_client)
            for contract in completed_contracts_list:
                # Get feedback from worker to client
                contract.worker_feedback = Feedback.objects.filter(
                    contract=contract,
                    giver=contract.worker,
                    receiver=user
                ).first()
            
            context["completed_contracts_client"] = completed_contracts_list
        
        return context

# Profile Update View
@method_decorator(login_required, name='dispatch')
class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = "users/profile_edit.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['education_formset'] = EducationFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='education')
            context['experience_formset'] = ExperienceFormSet(self.request.POST, self.request.FILES, instance=self.object, prefix='experience')
        else:
            context['education_formset'] = EducationFormSet(instance=self.object, prefix='education')
            context['experience_formset'] = ExperienceFormSet(instance=self.object, prefix='experience')
        return context

    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        
        context = self.get_context_data()
        education_formset = context['education_formset']
        experience_formset = context['experience_formset']
        
        if education_formset.is_valid() and experience_formset.is_valid():
            # Save the user profile first
            self.object = form.save(commit=False)
            self.object.save()
            
            # Save the formsets
            education_formset.instance = self.object
            education_formset.save()
            experience_formset.instance = self.object
            experience_formset.save()
            
            # Mark profile as completed when saving during onboarding
            # This must be done AFTER form.save() to ensure it persists
            if self.request.GET.get('onboarding') == 'true':
                logger.info(f"[ONBOARDING] User {self.object.pk} completing profile setup")
                self.object.profile_completed = True
                self.object.save(update_fields=['profile_completed'])
                logger.info(f"[ONBOARDING] User {self.object.pk} profile_completed set to: {self.object.profile_completed}")
                messages.success(self.request, 'Welcome! Your profile setup is complete. You can now explore TrabahoLink!')
            else:
                # Check if CV was uploaded
                if form.cleaned_data.get('cv_file'):
                    messages.success(self.request, 'Your profile and CV have been updated successfully!')
                else:
                    messages.success(self.request, 'Your profile has been updated successfully!')
            
            return super().form_valid(form)
        else:
            logger.warning(f"[ONBOARDING] Form validation failed for user {self.request.user.pk}")
            logger.warning(f"Education formset errors: {education_formset.errors}")
            logger.warning(f"Experience formset errors: {experience_formset.errors}")
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        # If coming from onboarding, redirect to home instead of profile view
        if self.request.GET.get('onboarding') == 'true':
            return reverse_lazy('jobs:home')
        return reverse_lazy('users:profile', kwargs={'pk': self.object.pk})

# Skill Verification View
@method_decorator(login_required, name='dispatch')
class SkillVerificationView(CreateView):
    model = Skill
    form_class = SkillVerificationForm
    template_name = "skills/submit_skill_verification.html"
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        # Get the skill ID from the URL if we're editing
        if 'pk' in self.kwargs:
            return get_object_or_404(Skill, pk=self.kwargs['pk'], user=self.request.user)
        return None

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Set the instance if we're editing
        if self.object:
            form.instance = self.object
        return form

    def get_initial(self):
        initial = super().get_initial()
        if self.object:
            initial.update({
                'name': self.object.name,
                'description': self.object.description,
            })
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['education_formset'] = EducationFormSet(self.request.POST, instance=self.request.user)
            context['experience_formset'] = ExperienceFormSet(self.request.POST, instance=self.request.user)
        else:
            context['education_formset'] = EducationFormSet(instance=self.request.user)
            context['experience_formset'] = ExperienceFormSet(instance=self.request.user)
        return context

    def form_valid(self, form):
        try:
            context = self.get_context_data()
            
            # Debug logs
            print("Form data:", form.cleaned_data)
            print("Files:", self.request.FILES)
            
            # Save the main form first
            self.object = form.save(commit=False)
            self.object.user = self.request.user
            self.object.status = 'pending'  # Set default status
            
            # Handle file upload
            if 'proof' in self.request.FILES:
                self.object.proof = self.request.FILES['proof']
            
            # Save the skill first
            self.object.save()
            
            # Save the formsets if they exist
            education_formset = context.get('education_formset')
            experience_formset = context.get('experience_formset')
            
            if education_formset:
                education_formset.instance = self.request.user
                if education_formset.is_valid():
                    education_formset.save()
                else:
                    print("Education formset errors:", education_formset.errors)
            
            if experience_formset:
                experience_formset.instance = self.request.user
                if experience_formset.is_valid():
                    experience_formset.save()
                else:
                    print("Experience formset errors:", experience_formset.errors)
            
            messages.success(self.request, "Skill verification submitted successfully!")
            return redirect(self.get_success_url())
            
        except Exception as e:
            print("Error in form submission:", str(e))
            messages.error(self.request, f"An error occurred while saving your skill: {str(e)}")
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})
    
    
# Profile Delete View
@method_decorator(login_required, name='dispatch')
class UserProfileDeleteView(DeleteView):
    model = CustomUser
    template_name = "users/profile_confirm_delete.html"
    success_url = reverse_lazy('login')

    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        """
        Override form_valid to handle historical records BEFORE deleting the user.
        This prevents foreign key constraint violations with django-simple-history.
        Especially important for social auth accounts.
        """
        user = self.get_object()
        
        # Import all models with historical records that reference users
        from jobs.models import Job, JobApplication, JobOffer
        from django.contrib.auth import logout
        from django.contrib import messages
        
        # Update all historical records that reference this user
        # Set history_user_id to None to prevent FK constraint violations
        models_with_history = [Job, JobApplication, JobOffer]
        
        for model in models_with_history:
            if hasattr(model, 'history'):
                # Update historical records to remove user reference
                model.history.filter(history_user=user).update(history_user=None)
        
        # Log the deletion for admin tracking
        messages.success(self.request, f"Account for {user.username} has been successfully deleted.")
        
        # Logout the user before deletion
        logout(self.request)
        
        # Now proceed with the normal deletion
        return super().form_valid(form)

# Submit Skill Verification
@login_required
def submit_skill_verification(request):
    if request.method == "POST":
        form = SkillVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('users:profile', pk=request.user.pk)
    else:
        form = SkillVerificationForm()
    return render(request, 'skills/submit_skill_verification.html', {'form': form})

# Skill Detail View
class SkillDetailView(LoginRequiredMixin, DetailView):
    model = Skill
    template_name = 'skills/skill_detail.html'
    context_object_name = 'skill'

# Skill Document Viewer
class SkillDocumentViewer(LoginRequiredMixin, View):
    def get(self, request, pk):
        skill = get_object_or_404(Skill, pk=pk)
        
        # Determine file type
        file_url = skill.proof.url
        file_extension = file_url.split('.')[-1].lower()
        
        if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            file_type = 'image'
        elif file_extension == 'pdf':
            file_type = 'pdf'
        else:
            file_type = 'other'
        
        context = {
            'file_url': file_url,
            'file_type': file_type,
            'skill': skill
        }
        
        return render(request, 'skills/document_viewer.html', context)

# Skill Update View
class SkillUpdateView(LoginRequiredMixin, UpdateView):
    model = Skill
    fields = ['name', 'description', 'proof']
    template_name = 'skills/skill_edit.html'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Skill.objects.all()
        return Skill.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

# Skill Delete View
class SkillDeleteView(LoginRequiredMixin, DeleteView):
    model = Skill
    template_name = 'skills/skill_delete.html'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Skill.objects.all()
        return Skill.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Create View
class CompletedJobGalleryCreateView(LoginRequiredMixin, CreateView):
    model = CompletedJobGallery
    form_class = CompletedJobGalleryForm
    template_name = "users/gallery_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Update View
class CompletedJobGalleryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CompletedJobGallery
    form_class = CompletedJobGalleryForm
    template_name = "users/gallery_form.html"

    def test_func(self):
        gallery_item = self.get_object()
        return gallery_item.user == self.request.user

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Delete View
class CompletedJobGalleryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CompletedJobGallery
    template_name = "users/gallery_confirm_delete.html"

    def test_func(self):
        gallery_item = self.get_object()
        return gallery_item.user == self.request.user

    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

# Job Notification Settings View (formerly User Location Update)
class UserLocationUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for managing job notification preferences
    WORKER ONLY - Only workers can set job notification preferences
    """
    template_name = "users/notification_settings.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Only allow workers to access this view
        if request.user.role != 'worker':
            messages.error(request, 'Job notifications are only available for workers. Employers do not need this feature.')
            return redirect('users:profile', pk=request.user.pk)
        return super().dispatch(request, *args, **kwargs)
    
    def get_object(self):
        # Get or create notification preference for user
        from .models import NotificationPreference
        pref, created = NotificationPreference.objects.get_or_create(user=self.request.user)
        return pref
    
    def get_form_class(self):
        from .forms import NotificationPreferenceForm
        return NotificationPreferenceForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from jobs.models import GeneralCategory
        import logging
        logger = logging.getLogger(__name__)
        
        # Get all general categories for display
        context['general_categories'] = GeneralCategory.objects.all().order_by('name')
        context['user'] = self.request.user
        
        # Get current preferences
        pref = self.get_object()
        context['current_radius'] = pref.notification_radius_km
        context['current_location'] = pref.notification_location
        context['selected_categories'] = pref.preferred_categories.all()
        
        logger.info(f"[NOTIFICATION_SETTINGS] User: {self.request.user.username}")
        logger.info(f"[NOTIFICATION_SETTINGS] Saved radius in DB: {pref.notification_radius_km} (type: {type(pref.notification_radius_km)})")
        logger.info(f"[NOTIFICATION_SETTINGS] Form initial value: {self.get_form().fields['notification_radius_km'].initial}")
        
        return context
    
    def form_valid(self, form):
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[NOTIFICATION_SETTINGS] Form submitted")
        logger.info(f"[NOTIFICATION_SETTINGS] Form cleaned_data radius: {form.cleaned_data.get('notification_radius_km')}")
        
        preference = form.save(commit=False)
        loc = form.cleaned_data.get('notification_location')
        
        if loc:
            try:
                # The form field already handles the WKT to GEOS conversion
                preference.notification_location = loc
            except Exception as e:
                form.add_error('notification_location', "Invalid location format.")
                return self.form_invalid(form)
        
        logger.info(f"[NOTIFICATION_SETTINGS] Before save - radius: {preference.notification_radius_km}")
        preference.save()
        logger.info(f"[NOTIFICATION_SETTINGS] After save - radius: {preference.notification_radius_km}")
        
        form.save_m2m()  # Save many-to-many relationships (preferred_categories)
        
        messages.success(
            self.request, 
            f'Your notification settings have been updated! You will receive alerts for jobs within {preference.notification_radius_km} km of your set location.'
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('users:set_location')  # Redirect back to settings page

# Identity Verification View
class IdentityVerificationView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = IdentityVerificationForm
    template_name = "users/identity_verification.html"

    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse_lazy('users:profile', kwargs={'pk': self.request.user.pk})

    def form_valid(self, form):
        user = form.save(commit=False)
        user.identity_verification_status = "pending"
        user.save()
        return redirect(self.get_success_url())
    


# Skip Identity Verification View
class SkipIdentityVerificationView(LoginRequiredMixin, View):
    # Simply mark the status as skipped and redirect.
    def get(self, request, *args, **kwargs):
        user = request.user
        user.identity_verification_status = "skipped"
        user.save()
        return redirect(reverse_lazy('users:profile', kwargs={'pk': user.pk}))


# User Search API View
@login_required
def search_users(request):
    """
    API endpoint to search for users by username or full name
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    # Search users excluding the current user
    users = CustomUser.objects.filter(
        Q(username__icontains=query) | 
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query)
    ).exclude(id=request.user.id)[:10]  # Limit to 10 results
    
    # Format user data for JSON response
    users_data = [{
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
    } for user in users]
    
    return JsonResponse({'users': users_data})


# ============================================
# File handling helpers for eKYC flow
# ============================================

TEMP_UPLOAD_DIR = 'verification/tmp/'
TEMP_DIR_PREFIX = os.path.normpath(TEMP_UPLOAD_DIR).replace('\\', '/')


TEMP_FILE_KEYS = {
    'front': 'temp_id_front_path',
    'back': 'temp_id_back_path',
    'selfie': 'temp_selfie_path',
}


def _ensure_temp_name(name):
    """Normalize and validate a temp file path to prevent traversal."""
    if not name:
        return None

    normalized = str(name).replace('\\', '/').lstrip('/')
    normalized = os.path.normpath(normalized)
    normalized = normalized.replace('\\', '/')

    # Reject attempts to leave temp directory
    if '..' in normalized.split('/'):
        raise SuspiciousFileOperation('Invalid temporary file reference.')

    if not normalized.startswith(TEMP_DIR_PREFIX):
        raise SuspiciousFileOperation('Invalid temporary file reference.')

    return normalized


def save_temporary_file(uploaded_file, prefix='temp'):
    """Save uploaded file to temporary storage and return relative path."""
    if not uploaded_file:
        return None

    ext = os.path.splitext(uploaded_file.name)[1]
    relative_name = os.path.join(TEMP_UPLOAD_DIR, f"{prefix}_{uuid.uuid4().hex}{ext}")
    safe_name = _ensure_temp_name(relative_name)

    stored_path = default_storage.save(safe_name, uploaded_file)
    return _ensure_temp_name(stored_path)


def open_temp_file(path):
    """Return a File object for the temporary file path, if it exists."""
    try:
        resolved = _ensure_temp_name(path)
    except SuspiciousFileOperation as exc:
        logger.warning("Rejected temporary file path: %s", exc)
        return None

    if not resolved or not default_storage.exists(resolved):
        return None

    try:
        storage_file = default_storage.open(resolved, 'rb')
        filename = os.path.basename(resolved)
        return File(storage_file, name=filename)
    except SuspiciousFileOperation as exc:
        logger.warning("Storage rejected temporary path %s: %s", resolved, exc)
    except FileNotFoundError:
        logger.warning("Temporary file %s disappeared before it could be processed.", resolved)
    return None


def cleanup_temp_files(session, keys):
    """Delete temporary files referenced in session and remove session keys."""
    for key in keys:
        stored = session.pop(key, None)
        try:
            path = _ensure_temp_name(stored)
        except SuspiciousFileOperation:
            path = None
        if path and default_storage.exists(path):
            default_storage.delete(path)


# ============================================
# eKYC VERIFICATION VIEWS
# ============================================

class VerificationStartView(LoginRequiredMixin, View):
    """Introduction page for eKYC verification"""
    template_name = 'users/ekyc_start.html'
    
    def get(self, request):
        # Check if user already has pending or approved verification
        latest_verification = request.user.verification_submissions.first()
        
        context = {
            'latest_verification': latest_verification,
            'user': request.user
        }
        return render(request, self.template_name, context)


class VerificationStep1View(LoginRequiredMixin, FormView):
    """Step 1: Personal Information"""
    template_name = 'users/ekyc_step1.html'
    form_class = VerificationStep1Form
    
    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['full_name'] = user.get_full_name() or user.username
        initial['contact_number'] = user.contact_number
        initial['address'] = user.address
        initial['gender'] = user.gender
        initial['date_of_birth'] = user.date_of_birth
        return initial
    
    def form_valid(self, form):
        # Store form data in session
        self.request.session['verification_step1'] = form.cleaned_data
        # Convert date to string for JSON serialization
        self.request.session['verification_step1']['date_of_birth'] = \
            form.cleaned_data['date_of_birth'].isoformat()
        return redirect('users:ekyc_step2')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = 1
        return context


class VerificationStep2View(LoginRequiredMixin, FormView):
    """Step 2: ID Upload"""
    template_name = 'users/ekyc_step2.html'
    form_class = VerificationStep2Form

    def dispatch(self, request, *args, **kwargs):
        # Ensure step 1 is completed
        if 'verification_step1' not in request.session:
            messages.warning(request, 'Please complete Step 1 first.')
            return redirect('users:ekyc_step1')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Store uploaded files temporarily
        request = self.request
        step2_data = {
            'id_type': form.cleaned_data['id_type']
        }
        
        # Handle PhilSys consent
        philsys_consent = request.POST.get('philsys_consent') == 'on'
        id_type = form.cleaned_data['id_type'].lower()
        is_philsys = id_type in ['philsys', 'philsys_id', 'national_id']
        
        if is_philsys:
            step2_data['philsys_consent'] = philsys_consent
            if philsys_consent:
                messages.info(
                    request,
                    'PhilSys automated verification will be performed after you complete all steps.'
                )
        else:
            step2_data['philsys_consent'] = False

        # Save files to temporary storage and keep path references in session
        id_front = form.cleaned_data['id_image_front']
        id_back = form.cleaned_data.get('id_image_back')

        # Clean up any previous files stored for this session
        cleanup_temp_files(request.session, ['temp_id_front_path', 'temp_id_back_path'])

        try:
            front_path = save_temporary_file(id_front, prefix='id_front')
            request.session['temp_id_front_path'] = front_path
            request.session['id_image_front'] = True

            if id_back:
                back_path = save_temporary_file(id_back, prefix='id_back')
                request.session['temp_id_back_path'] = back_path
                request.session['id_image_back'] = True
            else:
                request.session.pop('temp_id_back_path', None)
                request.session.pop('id_image_back', None)
        except SuspiciousFileOperation:
            messages.error(request, 'We detected an invalid ID image upload. Please try again.')
            cleanup_temp_files(request.session, ['temp_id_front_path', 'temp_id_back_path'])
            return redirect('users:ekyc_step2')

        request.session['verification_step2'] = step2_data
        return redirect('users:ekyc_step3')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = 2
        return context


class VerificationStep3View(LoginRequiredMixin, FormView):
    """Step 3: Selfie Verification"""
    template_name = 'users/ekyc_step3.html'
    form_class = VerificationStep3Form

    def dispatch(self, request, *args, **kwargs):
        # Ensure previous steps are completed
        if 'verification_step1' not in request.session or 'verification_step2' not in request.session:
            messages.warning(request, 'Please complete previous steps first.')
            return redirect('users:ekyc_step1')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request
        selfie = form.cleaned_data['selfie_image']

        cleanup_temp_files(request.session, ['temp_selfie_path'])
        try:
            selfie_path = save_temporary_file(selfie, prefix='selfie')
        except SuspiciousFileOperation:
            messages.error(request, 'Invalid selfie upload detected. Please retake your selfie.')
            return redirect('users:ekyc_step3')
        request.session['temp_selfie_path'] = selfie_path

        return redirect('users:ekyc_step4')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_step'] = 3
        return context


class VerificationStep4View(LoginRequiredMixin, View):
    """Step 4: Review and Submit"""
    template_name = 'users/ekyc_step4.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Ensure all previous steps are completed
        if not all(key in request.session for key in ['verification_step1', 'verification_step2']):
            messages.warning(request, 'Please complete all previous steps.')
            return redirect('users:ekyc_step1')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        from datetime import datetime
        
        try:
            step1_data = request.session.get('verification_step1', {})
            step2_data = request.session.get('verification_step2', {})
            
            # Validate that we have required data
            if not step1_data or not step2_data:
                messages.error(request, 'Session data is missing. Please start the verification process again.')
                return redirect('users:ekyc_step1')
            
            # Convert date string back to date object for display
            if 'date_of_birth' in step1_data and isinstance(step1_data['date_of_birth'], str):
                try:
                    step1_data['date_of_birth'] = datetime.fromisoformat(step1_data['date_of_birth']).date()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing date_of_birth: {e}")
                    step1_data['date_of_birth'] = None
            
            # Get ID type display name with error handling
            id_type_key = step2_data.get('id_type', '')
            try:
                id_type_display = dict(VALID_ID_CHOICES).get(id_type_key, id_type_key or 'Unknown')
            except Exception as e:
                logger.error(f"Error getting ID type display: {e}")
                id_type_display = id_type_key or 'Unknown'

            context = {
                'current_step': 4,
                'step1_data': step1_data,
                'step2_data': step2_data,
                'id_type_display': id_type_display,
                'id_front_uploaded': request.session.get('id_image_front', False),
                'id_back_uploaded': request.session.get('id_image_back', False),
                'selfie_uploaded': 'temp_selfie_path' in request.session,
            }
            return render(request, self.template_name, context)
            
        except Exception as e:
            logger.error(f"Error in VerificationStep4View.get: {e}", exc_info=True)
            messages.error(request, 'An error occurred while loading the review page. Please try again.')
            return redirect('users:ekyc_step1')
    
    def post(self, request):
        from datetime import datetime
        
        try:
            # Retrieve all session data
            step1_data = request.session.get('verification_step1', {})
            step2_data = request.session.get('verification_step2', {})
            
            # Validate required data
            if not step1_data or not step2_data:
                messages.error(request, 'Session data is missing. Please start the verification process again.')
                return redirect('users:ekyc_step1')
            
            # Convert date string back to date object
            if isinstance(step1_data.get('date_of_birth'), str):
                try:
                    step1_data['date_of_birth'] = datetime.fromisoformat(step1_data['date_of_birth']).date()
                except (ValueError, TypeError) as e:
                    logger.error(f"Error parsing date_of_birth: {e}")
                    messages.error(request, 'Invalid date format. Please start again.')
                    return redirect('users:ekyc_step1')
            
            # Load temporary files from storage
            id_front_path = request.session.get('temp_id_front_path')
            id_back_path = request.session.get('temp_id_back_path')
            selfie_path = request.session.get('temp_selfie_path')

            id_front_file = open_temp_file(id_front_path) if id_front_path else None
            id_back_file = open_temp_file(id_back_path) if id_back_path else None
            selfie_file = open_temp_file(selfie_path) if selfie_path else None

            if not id_front_file or not selfie_file:
                messages.error(request, 'We could not process your uploaded files. Please upload them again.')
                cleanup_temp_files(request.session, ['temp_id_front_path', 'temp_id_back_path', 'temp_selfie_path'])
                return redirect('users:ekyc_step2')

            # Create verification submission
            verification = AccountVerification.objects.create(
                user=request.user,
                full_name=step1_data['full_name'],
                date_of_birth=step1_data['date_of_birth'],
                address=step1_data['address'],
                contact_number=step1_data['contact_number'],
                gender=step1_data['gender'],
                id_type=step2_data['id_type'],
                id_image_front=id_front_file,
                id_image_back=id_back_file,
                selfie_image=selfie_file,
                status='pending'
            )

            # Persist ID/selfie images to user profile for pipeline processing
            user = request.user
            user.id_type = step2_data['id_type']
            user.id_image = verification.id_image_front
            user.selfie_image = verification.selfie_image
            user.verification_status = 'pending'
            user.save(update_fields=['id_type', 'id_image', 'selfie_image', 'verification_status'])

            # Queue verification pipeline to run in background (async)
            from users.tasks import run_verification_pipeline
            from users.tasks_philsys_auto import auto_verify_philsys
            
            try:
                # If PhilSys ID, chain tasks: face recognition -> PhilSys verification
                # This ensures face recognition completes BEFORE PhilSys verification runs
                if user.id_type == 'philsys' and verification.id_image_back:
                    from celery import chain
                    verification_chain = chain(
                        run_verification_pipeline.si(user_id=user.id, verification_id=verification.id),
                        auto_verify_philsys.si(verification_id=verification.id)
                    )
                    task = verification_chain.apply_async()
                    logger.info(
                        f"Chained verification (face recognition -> PhilSys) queued for user {user.id}"
                    )
                    messages.success(
                        request,
                        'Your PhilSys ID verification has been submitted! We are verifying your ID with the government portal. '
                        'You will receive a notification once verification is complete (usually within a few minutes).'
                    )
                else:
                    # For non-PhilSys IDs, just run the standard verification pipeline
                    task = run_verification_pipeline.delay(
                        user_id=user.id,
                        verification_id=verification.id
                    )
                    logger.info(
                        f"Verification pipeline queued for user {user.id} (task: {task.id})"
                    )
                    messages.success(
                        request,
                        'Your verification has been submitted! We are processing your documents in the background. '
                        'You will receive a notification once the verification is complete (usually within a few minutes).'
                    )
                
            except Exception as e:
                # If Celery is not available, log error and set for manual review
                logger.exception(f"Failed to queue verification task for user {user.id}: {e}")
                messages.warning(
                    request,
                    "Your verification has been submitted and will be reviewed by our team manually."
                )
            
            # Send notification to admins
            admin_users = CustomUser.objects.filter(role='admin')
            for admin in admin_users:
                Notification.objects.create(
                    user=admin,
                    message=f"New verification submission from {request.user.username}",
                    notif_type="verification",
                    object_id=verification.id
                )
            
            # Clear session data
            cleanup_temp_files(request.session, ['temp_id_front_path', 'temp_id_back_path', 'temp_selfie_path'])
            for key in ['verification_step1', 'verification_step2', 'id_image_front', 'id_image_back']:
                request.session.pop(key, None)

            # Redirect immediately to pending page
            return redirect('users:ekyc_pending')
            
        except Exception as e:
            logger.error(f"Error in VerificationStep4View.post: {e}", exc_info=True)
            messages.error(request, 'An error occurred while submitting your verification. Please try again.')
            return redirect('users:ekyc_step4')


class VerificationPendingView(LoginRequiredMixin, View):
    """Pending verification status page"""
    template_name = 'users/ekyc_pending.html'
    
    def get(self, request):
        latest_verification = request.user.verification_submissions.first()
        context = {
            'verification': latest_verification
        }
        return render(request, self.template_name, context)


class VerificationSuccessView(LoginRequiredMixin, View):
    """Verification success page"""
    template_name = 'users/ekyc_success.html'
    
    def get(self, request):
        return render(request, self.template_name)


class VerificationFailedView(LoginRequiredMixin, View):
    """Verification failed/rejected page"""
    template_name = 'users/ekyc_failed.html'
    
    def get(self, request):
        latest_verification = request.user.verification_submissions.filter(
            status='rejected'
        ).first()
        
        context = {
            'verification': latest_verification
        }
        return render(request, self.template_name, context)


# OTP Verification Views
class VerifyOTPView(View):
    """View to verify OTP code during registration"""
    template_name = 'users/verify_otp.html'
    
    def get(self, request, email):
        # Normalize email from URL
        from urllib.parse import unquote
        email = unquote(email).lower().strip()
        
        context = {
            'email': email
        }
        return render(request, self.template_name, context)
    
    def post(self, request, email):
        from .otp_utils import verify_otp
        from django.contrib.auth import login, get_backends
        from urllib.parse import unquote
        
        # Normalize email from URL
        email = unquote(email).lower().strip()
        
        otp_code = request.POST.get('otp_code', '').strip()
        
        if not otp_code:
            messages.error(request, 'Please enter the verification code.')
            return redirect('verify_otp', email=email)
        
        # Verify OTP
        success, message, otp_record = verify_otp(email, otp_code)
        
        if success and otp_record:
            # Check if user already exists
            existing_user = CustomUser.objects.filter(
                models.Q(username=otp_record.username) | models.Q(email=otp_record.email)
            ).first()
            
            if existing_user:
                # User already exists and email is already verified
                messages.info(request, 'This email is already registered. Please login instead.')
                return redirect('users:login')
            
            # Create the user account
            try:
                user = CustomUser.objects.create(
                    username=otp_record.username,
                    email=otp_record.email,
                    password=otp_record.password_hash,  # Already hashed
                    role=otp_record.role,
                    role_selected=True,  # Regular users explicitly select role during registration
                    is_active=True,
                    # Set default values for verification fields
                    identity_verification_status='pending',
                    verification_status='pending',
                    face_detected=False,
                    ocr_confidence_score=0,
                    is_verified=False,
                    is_verified_philsys=False
                )
                
                # Log the user in
                backend = get_backends()[0]
                user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
                login(request, user)
                
                messages.success(request, 'Email verified successfully! Welcome to TrabahoLink.')
                
                # Redirect to home page instead of forcing identity verification
                # User can verify identity later from their profile
                return redirect('jobs:home')
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating account for {otp_record.email}: {str(e)}")
                messages.error(request, f'Error creating account: {str(e)}')
                return redirect('users:register')
        else:
            messages.error(request, message)
            return redirect('verify_otp', email=email)


class ResendOTPView(View):
    """View to resend OTP code"""
    
    def post(self, request, email):
        from .otp_utils import resend_otp
        
        success, message = resend_otp(email)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
        
        return redirect('verify_otp', email=email)


# ============================================
# SOCIAL ACCOUNT ROLE SELECTION
# ============================================

@login_required
def select_role_view(request):
    """
    View for new social account users to select their role.
    This is shown after Google OAuth signup.
    """
    # If user already has role_selected, redirect them away
    if request.user.role_selected:
        messages.info(request, 'You have already selected your role.')
        return redirect('jobs:home')
    
    # Clear the session flag
    needs_selection = request.session.pop('needs_role_selection', False)
    
    if request.method == 'POST':
        role = request.POST.get('role')
        
        if role in ['client', 'worker']:
            request.user.role = role
            request.user.role_selected = True  # Mark that role has been selected
            request.user.save()
            
            messages.success(request, f'Welcome! You have joined as a {role.title()}.')
            return redirect('jobs:home')
        else:
            messages.error(request, 'Please select a valid role.')
    
    return render(request, 'users/select_role.html', {
        'needs_selection': needs_selection
    })


# ============================================================================
# USER GUIDE MANAGEMENT VIEWS
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def disable_guide_auto_popup(request):
    """
    Disable auto-popup for the current user.
    
    AJAX endpoint called when user clicks "Don't show this again"
    
    Returns:
        JSON: {success: bool, message: str}
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)
    
    try:
        # Get or create guide status
        from .models import UserGuideStatus
        guide_status, created = UserGuideStatus.objects.get_or_create(user=request.user)
        guide_status.disable_auto_popup()
        
        return JsonResponse({
            'success': True,
            'message': 'Auto-popup disabled successfully. You can still access guides using the help button.',
            'auto_popup_enabled': False
        })
    except Exception as e:
        logger.error(f"Error disabling guide auto-popup for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error disabling auto-popup: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def enable_guide_auto_popup(request):
    """
    Re-enable auto-popup for the current user.
    
    AJAX endpoint for users who want to turn auto-popup back on.
    
    Returns:
        JSON: {success: bool, message: str}
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)
    
    try:
        # Get or create guide status
        from .models import UserGuideStatus
        guide_status, created = UserGuideStatus.objects.get_or_create(user=request.user)
        guide_status.enable_auto_popup()
        
        return JsonResponse({
            'success': True,
            'message': 'Auto-popup enabled successfully.',
            'auto_popup_enabled': True
        })
    except Exception as e:
        logger.error(f"Error enabling guide auto-popup for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error enabling auto-popup: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_guide_progress(request):
    """
    Update user's guide progress for a specific page.
    
    Expected POST data:
        {
            "page_name": "job_list",
            "step": 2,
            "completed": false
        }
    
    Returns:
        JSON: {success: bool, message: str}
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        page_name = data.get('page_name')
        step = data.get('step', 0)
        completed = data.get('completed', False)
        
        if not page_name:
            return JsonResponse({
                'success': False,
                'message': 'page_name is required'
            }, status=400)
        
        # Get or create guide status
        from .models import UserGuideStatus
        guide_status, created = UserGuideStatus.objects.get_or_create(user=request.user)
        
        if completed:
            guide_status.mark_page_completed(page_name, step)
        else:
            guide_status.update_progress(page_name, step)
        
        return JsonResponse({
            'success': True,
            'message': 'Progress updated successfully',
            'page_name': page_name,
            'step': step,
            'completed': completed
        })
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in update_guide_progress for user {request.user.id}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating guide progress for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error updating progress: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_guide_status(request):
    """
    Get current guide status for the user.
    
    Returns:
        JSON: Complete guide status information
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)
    
    try:
        # Get or create guide status
        from .models import UserGuideStatus
        guide_status, created = UserGuideStatus.objects.get_or_create(user=request.user)
        
        return JsonResponse({
            'success': True,
            'data': {
                'auto_popup_enabled': guide_status.auto_popup_enabled,
                'last_page_viewed': guide_status.last_page_viewed,
                'last_step_completed': guide_status.last_step_completed,
                'pages_completed': guide_status.pages_completed,
                'total_guides_viewed': guide_status.total_guides_viewed,
            }
        })
    except Exception as e:
        logger.error(f"Error fetching guide status for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error fetching guide status: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def increment_guide_view_count(request):
    """
    Increment the total guide view counter.
    
    Called each time user opens a guide.
    
    Returns:
        JSON: {success: bool, total_views: int}
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'message': 'Authentication required'
        }, status=401)
    
    try:
        # Get or create guide status
        from .models import UserGuideStatus
        guide_status, created = UserGuideStatus.objects.get_or_create(user=request.user)
        guide_status.increment_view_count()
        
        return JsonResponse({
            'success': True,
            'total_views': guide_status.total_guides_viewed
        })
    except Exception as e:
        logger.error(f"Error incrementing guide view count for user {request.user.id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error incrementing view count: {str(e)}'
        }, status=500)

@login_required
def skip_profile_setup(request):
    """
    Allow users to skip initial profile setup.
    Marks profile as completed even if not fully filled.
    """
    # Allow both GET and POST for better UX
    if request.method in ['POST', 'GET']:
        request.user.profile_completed = True
        request.user.save(update_fields=['profile_completed'])
        messages.success(request, 'You can complete your profile anytime from your account settings.')
        return redirect('jobs:home')
    
    # Fallback redirect
    return redirect('jobs:home')
