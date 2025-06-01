from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .forms import ServicePostForm
from .models import ServicePost, ServicePostImage

class ServicePostListView(ListView):
    model = ServicePost
    template_name = "services/servicepost_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        return ServicePost.objects.filter(is_active=True).order_by("-created_at")

class ServicePostCreateView(LoginRequiredMixin, CreateView):
    model = ServicePost
    form_class = ServicePostForm
    template_name = "services/create_post.html"
    
    def form_valid(self, form):
        form.instance.worker = self.request.user
        form.instance.is_active = True
        # Process location and images...
        latitude = self.request.POST.get('latitude')
        longitude = self.request.POST.get('longitude')
        if latitude and longitude:
            try:
                form.instance.location = Point(float(longitude), float(latitude))
            except ValueError as e:
                messages.error(self.request, "Invalid location coordinates.")
                return self.form_invalid(form)
        else:
            messages.error(self.request, "Location data is required.")
            return self.form_invalid(form)
        response = super().form_valid(form)
        transaction.on_commit(lambda: self.save_images(self.object))
        messages.success(self.request, "Service advertisement created successfully.")
        return response

    def save_images(self, service_post):
        images = self.request.FILES.getlist('images')
        if images:
            for img in images:
                try:
                    ServicePostImage.objects.create(service_post=service_post, image=img)
                    print("DEBUG: Saved image", img.name)
                except Exception as e:
                    messages.error(self.request, f"Failed to save image {img.name}.")
                    print("DEBUG: Failure saving image:", img.name, e)
        else:
            print("DEBUG: No images were uploaded.")

    def get_success_url(self):
        return reverse("jobs:job_list")

class ServicePostDetailView(DetailView):
    model = ServicePost
    template_name = "services/servicepost_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    context_object_name = "post"  # Now your template can use {{ post.headline }}, etc.

class ServicePostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ServicePost
    form_class = ServicePostForm
    template_name = "services/servicepost_form.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    
    def form_valid(self, form):
        form.instance.worker = self.request.user
        
        # Process updated location from hidden fields
        latitude = self.request.POST.get('latitude')
        longitude = self.request.POST.get('longitude')
        if latitude and longitude:
            try:
                form.instance.location = Point(float(longitude), float(latitude))
            except ValueError:
                messages.error(self.request, "Invalid location coordinates.")
                return self.form_invalid(form)
        else:
            messages.error(self.request, "Location data is required.")
            return self.form_invalid(form)

        response = super().form_valid(form)
        
        # Process new images
        images = self.request.FILES.getlist('images')
        if images:
            for img in images:
                try:
                    ServicePostImage.objects.create(service_post=self.object, image=img)
                except Exception as e:
                    messages.error(self.request, f"Failed to save image {img.name}. {e}")
        messages.success(self.request, "Service post updated successfully.")
        return response

    def test_func(self):
        post = self.get_object()
        return post.worker == self.request.user

    def get_success_url(self):
        return reverse("jobs:job_list")

class ServicePostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ServicePost
    template_name = "services/servicepost_confirm_delete.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    
    def test_func(self):
        post = self.get_object()
        return post.worker == self.request.user
    
    def get_success_url(self):
        messages.info(self.request, "Service post has been deleted.")
        return reverse_lazy("services:servicepost_list")

# Optional function-based view for deactivating a post.
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

@login_required
def deactivate_service_post(request, slug):
    post = get_object_or_404(ServicePost, slug=slug, worker=request.user)
    post.is_active = False
    post.save()
    messages.info(request, "Service post has been deactivated.")
    return redirect("services:servicepost_list")
