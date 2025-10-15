from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .forms import ServicePostForm
from .models import ServicePost, ServicePostImage
from admin_dashboard.moderation_utils import check_for_banned_words

class ServicePostListView(ListView):
    model = ServicePost
    template_name = "services/servicepost_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        return ServicePost.objects.filter(is_active=True, status='approved').order_by("-created_at")

class MyServicesListView(LoginRequiredMixin, ListView):
    model = ServicePost
    template_name = "services/my_services.html"
    context_object_name = "services"
    paginate_by = 12

    def get_queryset(self):
        return ServicePost.objects.filter(worker=self.request.user).order_by("-created_at")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = self.get_queryset().filter(status='pending').count()
        context['approved_count'] = self.get_queryset().filter(status='approved').count()
        context['rejected_count'] = self.get_queryset().filter(status='rejected').count()
        context['total_count'] = self.get_queryset().count()
        return context

class ServicePostCreateView(LoginRequiredMixin, CreateView):
    model = ServicePost
    form_class = ServicePostForm
    template_name = "services/create_post.html"
    
    def form_valid(self, form):
        try:
            # Check for banned words in headline
            headline = form.cleaned_data.get('headline', '')
            description = form.cleaned_data.get('description', '')
            
            is_flagged_headline, flagged_words_headline = check_for_banned_words(headline)
            is_flagged_desc, flagged_words_desc = check_for_banned_words(description)
            
            # Combine all flagged words
            all_flagged = set(flagged_words_headline + flagged_words_desc)
            
            if all_flagged:
                messages.error(
                    self.request,
                    f"Your service post contains inappropriate words: {', '.join(all_flagged)}. Please remove them and try again."
                )
                return self.form_invalid(form)
            
            form.instance.worker = self.request.user
            form.instance.status = 'pending'  # Set to pending for admin review
            form.instance.is_active = False  # Will be activated when approved
            
            # Process location
            latitude = self.request.POST.get('latitude')
            longitude = self.request.POST.get('longitude')
            
            if latitude and longitude:
                try:
                    form.instance.location = Point(float(longitude), float(latitude))
                except (ValueError, TypeError) as e:
                    messages.error(self.request, f"Invalid location coordinates: {str(e)}")
                    return self.form_invalid(form)
            else:
                messages.error(self.request, "Location data is required. Please set a location on the map.")
                return self.form_invalid(form)
            
            response = super().form_valid(form)
            transaction.on_commit(lambda: self.save_images(self.object))
            messages.success(self.request, "Service created successfully! It will be reviewed by an admin before going live.")
            return response
            
        except Exception as e:
            messages.error(self.request, f"Error creating service: {str(e)}")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Show form errors to user
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

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
        return reverse("services:my_services")

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
        try:
            # Check for banned words in headline
            headline = form.cleaned_data.get('headline', '')
            description = form.cleaned_data.get('description', '')
            
            is_flagged_headline, flagged_words_headline = check_for_banned_words(headline)
            is_flagged_desc, flagged_words_desc = check_for_banned_words(description)
            
            # Combine all flagged words
            all_flagged = set(flagged_words_headline + flagged_words_desc)
            
            if all_flagged:
                messages.error(
                    self.request,
                    f"Your service post contains inappropriate words: {', '.join(all_flagged)}. Please remove them and try again."
                )
                return self.form_invalid(form)
            
            form.instance.worker = self.request.user
            
            # Process updated location from hidden fields
            latitude = self.request.POST.get('latitude')
            longitude = self.request.POST.get('longitude')
            
            if latitude and longitude:
                try:
                    form.instance.location = Point(float(longitude), float(latitude))
                except (ValueError, TypeError) as e:
                    messages.error(self.request, f"Invalid location coordinates: {str(e)}")
                    return self.form_invalid(form)
            else:
                messages.error(self.request, "Location data is required. Please set a location on the map.")
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
            
        except Exception as e:
            messages.error(self.request, f"Error updating service: {str(e)}")
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        # Show form errors to user
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f"{field}: {error}")
        return super().form_invalid(form)

    def test_func(self):
        post = self.get_object()
        return post.worker == self.request.user

    def get_success_url(self):
        return reverse("services:my_services")

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
    return redirect("jobs:job_list")
