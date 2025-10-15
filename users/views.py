from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash, get_backends
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import CreateView, UpdateView, DetailView, DeleteView, FormView
from django.forms import inlineformset_factory, DateInput
from django.conf import settings
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied, SuspiciousFileOperation
from django.contrib.gis.geos import GEOSGeometry
from django.http import JsonResponse
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.base import File
import uuid
import os
import logging

from .models import CustomUser, Skill, Education, Experience, CompletedJobGallery, AccountVerification
from .forms import (CustomUserRegistrationForm, IdentityVerificationForm, UserProfileForm, 
                   SkillVerificationForm, CompletedJobGalleryForm, UserLocationForm,
                   VerificationStep1Form, VerificationStep2Form, VerificationStep3Form)
from jobs.models import JobApplication, Contract, Feedback
from notifications.models import Notification

logger = logging.getLogger(__name__)

# Formsets for education and experience
EducationFormSet = inlineformset_factory(
    CustomUser,
    Education,
    fields=('degree', 'institution', 'start_date', 'end_date', 'description'),
    extra=1,
    can_delete=True,
    widgets={
        'degree': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g. Bachelor of Science in Computer Science'
        }),
        'institution': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter the institution name'
        }),
        'start_date': DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'placeholder': 'Select start date'
        }),
        'end_date': DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'placeholder': 'Select end date (or leave blank if ongoing)'
        }),
        'description': forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Additional details about your studies'
        }),
    }
)

ExperienceFormSet = inlineformset_factory(
    CustomUser,
    Experience,
    fields=('job_title', 'company', 'start_date', 'end_date', 'description'),
    extra=1,
    can_delete=True,
    widgets={
        'job_title': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'e.g. Software Engineer'
        }),
        'company': forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Enter the company name'
        }),
        'start_date': DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'placeholder': 'Select start date'
        }),
        'end_date': DateInput(attrs={
            'type': 'date', 
            'class': 'form-control', 
            'placeholder': 'Select end date (or leave blank if current)'
        }),
        'description': forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3, 
            'placeholder': 'Describe your role and responsibilities'
        }),
    }
)

# Register View
class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = CustomUserRegistrationForm

    def form_valid(self, form):
        user = form.save()
        backend = get_backends()[0]
        user.backend = f"{backend.__module__}.{backend.__class__.__name__}"
        login(self.request, user)
        return redirect('identity_verification', pk=user.pk)

# Login View
class UserLoginView(LoginView):
    template_name = "users/login.html"

# Logout View
class UserLogoutView(LogoutView):
    template_name = "users/logout.html"

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
        return reverse('profile_edit', kwargs={'pk': self.request.user.pk})

# Privacy Settings View
@method_decorator(login_required, name='dispatch')
class PrivacySettingsView(UpdateView):
    model = CustomUser
    form_class = UserProfileForm 
    template_name = "users/privacy_settings.html"

    def get_object(self):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('profile')

# Profile Detail View
@method_decorator(login_required, name='dispatch')
class UserProfileDetailView(DetailView):
    model = CustomUser
    template_name = "users/profile_detail.html"
    context_object_name = "user"

    def get_object(self):
        return get_object_or_404(CustomUser, pk=self.kwargs['pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        context["recent_applications"] = JobApplication.objects.filter(worker=user).select_related("job").order_by("-applied_at")[:5]
        context["posted_jobs"] = user.posted_jobs.order_by("-created_at")
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
        context = self.get_context_data()
        education_formset = context['education_formset']
        experience_formset = context['experience_formset']
        
        if education_formset.is_valid() and experience_formset.is_valid():
            self.object = form.save()
            education_formset.instance = self.object
            education_formset.save()
            experience_formset.instance = self.object
            experience_formset.save()
            messages.success(self.request, 'Your profile has been updated successfully!')
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.object.pk})

# Skill Verification View
@method_decorator(login_required, name='dispatch')
class SkillVerificationView(CreateView):
    model = Skill
    form_class = SkillVerificationForm
    template_name = "skills/submit_skill_verification.html"
    success_url = reverse_lazy('profile')

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
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})
    
    
# Profile Delete View
@method_decorator(login_required, name='dispatch')
class UserProfileDeleteView(DeleteView):
    model = CustomUser
    template_name = "users/profile_confirm_delete.html"
    success_url = reverse_lazy('login')

    def get_object(self):
        return self.request.user

# Submit Skill Verification
@login_required
def submit_skill_verification(request):
    if request.method == "POST":
        form = SkillVerificationForm(request.POST, request.FILES)
        if form.is_valid():
            skill = form.save(commit=False)
            skill.user = request.user
            skill.save()
            return redirect('profile', pk=request.user.pk)
    else:
        form = SkillVerificationForm()
    return render(request, 'skills/submit_skill_verification.html', {'form': form})

# Skill Detail View
class SkillDetailView(LoginRequiredMixin, DetailView):
    model = Skill
    template_name = 'skills/skill_detail.html'
    context_object_name = 'skill'

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
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# Skill Delete View
class SkillDeleteView(LoginRequiredMixin, DeleteView):
    model = Skill
    template_name = 'skills/skill_delete.html'

    def get_queryset(self):
        if self.request.user.is_staff:
            return Skill.objects.all()
        return Skill.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Create View
class CompletedJobGalleryCreateView(LoginRequiredMixin, CreateView):
    model = CompletedJobGallery
    form_class = CompletedJobGalleryForm
    template_name = "users/gallery_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Update View
class CompletedJobGalleryUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CompletedJobGallery
    form_class = CompletedJobGalleryForm
    template_name = "users/gallery_form.html"

    def test_func(self):
        gallery_item = self.get_object()
        return gallery_item.user == self.request.user

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# Completed Job Gallery Delete View
class CompletedJobGalleryDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CompletedJobGallery
    template_name = "users/gallery_confirm_delete.html"

    def test_func(self):
        gallery_item = self.get_object()
        return gallery_item.user == self.request.user

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# User Location Update View
class UserLocationUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = UserLocationForm
    template_name = "users/set_location.html"

    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        user = form.save(commit=False)
        loc = form.cleaned_data.get('location')
        print("DEBUG: Posted location is:", loc)  # Debugging output in console
        
        if loc:
            try:
                # The form field already handles the WKT to GEOS conversion
                user.location = loc
                print("DEBUG: Parsed location:", user.location.wkt if user.location else "None")
            except Exception as e:
                print("DEBUG: Error parsing location:", e)
                form.add_error('location', "Invalid location format.")
                return self.form_invalid(form)
                
        user.save()
        print("DEBUG: User saved with location:", user.location.wkt if user.location else "None")
        messages.success(self.request, 'Your location has been updated successfully!')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

# Identity Verification View
class IdentityVerificationView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = IdentityVerificationForm
    template_name = "users/identity_verification.html"

    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.pk})

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
        return redirect(reverse_lazy('profile', kwargs={'pk': user.pk}))


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
        return redirect('ekyc_step2')
    
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
            return redirect('ekyc_step1')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Store uploaded files temporarily
        request = self.request
        step2_data = {
            'id_type': form.cleaned_data['id_type']
        }

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
            return redirect('ekyc_step2')

        request.session['verification_step2'] = step2_data
        return redirect('ekyc_step3')
    
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
            return redirect('ekyc_step1')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        request = self.request
        selfie = form.cleaned_data['selfie_image']

        cleanup_temp_files(request.session, ['temp_selfie_path'])
        try:
            selfie_path = save_temporary_file(selfie, prefix='selfie')
        except SuspiciousFileOperation:
            messages.error(request, 'Invalid selfie upload detected. Please retake your selfie.')
            return redirect('ekyc_step3')
        request.session['temp_selfie_path'] = selfie_path

        return redirect('ekyc_step4')
    
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
            return redirect('ekyc_step1')
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request):
        from datetime import datetime
        
        step1_data = request.session.get('verification_step1', {})
        step2_data = request.session.get('verification_step2', {})
        
        # Convert date string back to date object for display
        if 'date_of_birth' in step1_data and isinstance(step1_data['date_of_birth'], str):
            step1_data['date_of_birth'] = datetime.fromisoformat(step1_data['date_of_birth']).date()
        
        id_type_key = step2_data.get('id_type')
        id_type_display = dict(AccountVerification.ID_TYPE_CHOICES).get(id_type_key, id_type_key)

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
    
    def post(self, request):
        from datetime import datetime
        
        # Retrieve all session data
        step1_data = request.session.get('verification_step1', {})
        step2_data = request.session.get('verification_step2', {})
        
        # Convert date string back to date object
        if isinstance(step1_data.get('date_of_birth'), str):
            step1_data['date_of_birth'] = datetime.fromisoformat(step1_data['date_of_birth']).date()
        
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
            return redirect('ekyc_step2')

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
        
        # Update user verification status
        request.user.verification_status = 'pending'
        request.user.save(update_fields=['verification_status'])
        
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

        messages.success(request, 'Verification submitted successfully! We will review your submission.')
        return redirect('ekyc_pending')


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