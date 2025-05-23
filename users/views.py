from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from django.contrib.auth import login, get_backends
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from jobs.models import JobApplication
from .models import CustomUser, Skill
from .forms import CustomUserRegistrationForm, UserProfileForm

# Change Password View
@method_decorator(login_required, name='dispatch')
class ChangePasswordView(UpdateView):
    template_name = "users/change_password.html"
    form_class = PasswordChangeForm

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)  # Important!
        return redirect('profile')

# Privacy Settings View

class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = CustomUserRegistrationForm

    def form_valid(self, form):
        user = form.save()

        backend = get_backends()[0]  
        user.backend = f"{backend.__module__}.{backend.__class__.__name__}"

        login(self.request, user)  
        return redirect('login')

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

class UserLoginView(LoginView):
    template_name = "users/login.html"

# User Logout View 
class UserLogoutView(LogoutView):
    template_name = "users/logout.html"

# Profile Detail View
@method_decorator(login_required, name='dispatch')
class UserProfileDetailView(DetailView):
    model = CustomUser
    template_name = "users/profile_detail.html"
    context_object_name = "user"

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()

        # Fetch recent jobs the user has applied for
        recent_applications = JobApplication.objects.filter(worker=user).select_related("job").order_by("-applied_at")[:5]
        context["recent_applications"] = recent_applications

        # Fetch jobs the user has posted
        context["posted_jobs"] = user.posted_jobs.order_by("-created_at")

        return context


@method_decorator(login_required, name='dispatch')
class UserProfileUpdateView(UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = "users/profile_edit.html"

    def get_object(self):
        return self.request.user

    def get_initial(self):
        initial = super().get_initial()
        skills = self.request.user.skills.values_list('name', flat=True)
        initial['skills'] = ','.join(skills) 
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        skill_names = self.request.POST.get('skills', '')
        skill_list = [s.strip() for s in skill_names.split(',') if s.strip()]
        skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in skill_list]
        self.object.skills.set(skill_objs)

        return response

    def get_success_url(self):
        return reverse_lazy('profile')

# Profile Delete View
@method_decorator(login_required, name='dispatch')
class UserProfileDeleteView(DeleteView):
    model = CustomUser
    template_name = "users/profile_confirm_delete.html"
    success_url = reverse_lazy('login')  
    def get_object(self):
        return self.request.user
