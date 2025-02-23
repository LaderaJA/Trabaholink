from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DetailView, DeleteView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import CustomUser
from .forms import CustomUserRegistrationForm, UserProfileForm

# User Registration View
class RegisterView(CreateView):
    template_name = "users/register.html"
    form_class = CustomUserRegistrationForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)  # Automatically log in user after registration
        return redirect('profile')

# User Login View (Django built-in)
class UserLoginView(LoginView):
    template_name = "users/login.html"

# User Logout View (Django built-in)
class UserLogoutView(LogoutView):
    template_name = "users/logout.html"

# Profile Detail View
@method_decorator(login_required, name='dispatch')
class UserProfileDetailView(DetailView):
    model = CustomUser
    template_name = "users/profile_detail.html"

    def get_object(self):
        return self.request.user  

# Profile Update View
@method_decorator(login_required, name='dispatch')
class UserProfileUpdateView(UpdateView):
    model = CustomUser
    form_class = UserProfileForm
    template_name = "users/profile_edit.html"

    def get_object(self):
        return self.request.user 

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