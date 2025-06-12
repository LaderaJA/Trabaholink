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
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.contrib.gis.geos import GEOSGeometry

from .models import CustomUser, Skill, Education, Experience, CompletedJobGallery
from .forms import CustomUserRegistrationForm, IdentityVerificationForm, UserProfileForm, SkillVerificationForm, CompletedJobGalleryForm, UserLocationForm
from jobs.models import JobApplication

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

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Skill verification submitted successfully!")
        return super().form_valid(form)

    def get_object(self):
        # Update current user only
        return self.request.user

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Allow partial update so missing fields do not trigger required errors
        form.partial = True
        return form

    def get_initial(self):
        initial = super().get_initial()
        # Prepopulate skills from the related Skill objects (adjust field/related name if needed)
        skills = self.request.user.skill_verifications.values_list('name', flat=True)
        initial['skills'] = ','.join(skills)
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
        context = self.get_context_data()
        education_formset = context.get('education_formset')
        experience_formset = context.get('experience_formset')
        
        if education_formset.is_valid() and experience_formset.is_valid():
            # Save main form partially; form.partial=True is set above.
            self.object = form.save()
            form.save_m2m()
            education_formset.instance = self.object
            experience_formset.instance = self.object
            education_formset.save()
            experience_formset.save()

            skill_input = self.request.POST.get('skills', '')
            skill_list = [s.strip() for s in skill_input.split(',') if s.strip()]
            skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in skill_list]
            self.object.skill_verifications.set(skill_objs)

            messages.success(self.request, "Profile updated successfully!")
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, "Please correct the errors below.")
            return self.render_to_response(self.get_context_data(form=form))

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