from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.contrib.gis.geos import Point
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.base import RedirectView
from .forms import ServicePostForm
from .models import ServicePost, ServicePostImage
from admin_dashboard.moderation_utils import check_for_banned_words

class ServicePostListView(RedirectView):
    """
    Redirect to the main job list page with services tab active.
    Services are now displayed in the unified job/service listing page.
    """
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        # Preserve query parameters and add tab=services
        query_params = self.request.GET.copy()
        query_params['tab'] = 'services'
        query_string = query_params.urlencode()
        return f"{reverse('jobs:job_list')}?{query_string}"

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
            # Check for banned words in headline and description
            headline = form.cleaned_data.get('headline', '')
            description = form.cleaned_data.get('description', '')
            availability = form.cleaned_data.get('availability', '')
            address = form.cleaned_data.get('address', '')
            
            # Check all text fields for banned words
            is_flagged_headline, flagged_words_headline = check_for_banned_words(headline)
            is_flagged_desc, flagged_words_desc = check_for_banned_words(description)
            is_flagged_avail, flagged_words_avail = check_for_banned_words(availability)
            is_flagged_addr, flagged_words_addr = check_for_banned_words(address)
            
            # Combine all flagged words
            all_flagged = set(
                flagged_words_headline + 
                flagged_words_desc + 
                flagged_words_avail + 
                flagged_words_addr
            )
            
            if all_flagged:
                messages.error(
                    self.request,
                    f"Your service post contains inappropriate words: {', '.join(all_flagged)}. Please remove them and try again."
                )
                return self.form_invalid(form)
            
            form.instance.worker = self.request.user
            
            # Auto-approve if no banned words detected
            form.instance.status = 'approved'
            form.instance.is_active = True
            
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
            messages.success(self.request, "Service created and published successfully! Your service is now live and visible to everyone.")
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
    
    def get_context_data(self, **kwargs):
        from .models import ServiceReview
        from .forms import ServiceReviewForm
        from django.db.models import Avg
        
        context = super().get_context_data(**kwargs)
        service_post = self.object
        
        # Get reviews (exclude hidden ones for regular users, show all for staff)
        if self.request.user.is_staff:
            reviews = service_post.reviews.all()
        else:
            reviews = service_post.reviews.filter(is_hidden=False)
        
        # Calculate average rating
        avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
        
        # Get rating distribution
        rating_counts = {i: 0 for i in range(1, 6)}
        for review in reviews:
            rating_counts[review.rating] = rating_counts.get(review.rating, 0) + 1
        
        # Check if current user has reviewed
        user_review = None
        if self.request.user.is_authenticated:
            user_review = reviews.filter(reviewer=self.request.user).first()
        
        context.update({
            'reviews': reviews,
            'review_count': reviews.count(),
            'avg_rating': avg_rating,
            'rating_counts': rating_counts,
            'user_review': user_review,
            'review_form': ServiceReviewForm() if self.request.user.is_authenticated and not user_review else None,
        })
        
        return context

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
            
            # Process image deletions
            delete_images = self.request.POST.getlist('delete_images')
            deleted_count = 0
            for image_id in delete_images:
                if image_id:  # Only process non-empty values
                    try:
                        image = ServicePostImage.objects.get(id=image_id, service_post=self.object)
                        image.delete()
                        deleted_count += 1
                    except ServicePostImage.DoesNotExist:
                        pass
                    except Exception as e:
                        messages.error(self.request, f"Failed to delete image: {str(e)}")
            
            # Process new images
            images = self.request.FILES.getlist('images')
            uploaded_count = 0
            print(f"DEBUG: Found {len(images)} images in request.FILES")
            print(f"DEBUG: request.FILES keys: {list(self.request.FILES.keys())}")
            
            if images:
                for img in images:
                    try:
                        new_image = ServicePostImage.objects.create(service_post=self.object, image=img)
                        uploaded_count += 1
                        print(f"DEBUG: Successfully saved image {img.name} with ID {new_image.id}")
                    except Exception as e:
                        print(f"DEBUG: Failed to save image {img.name}: {str(e)}")
                        messages.error(self.request, f"Failed to save image {img.name}. {e}")
            else:
                print("DEBUG: No images found in request.FILES")
            
            # Success message with details
            success_parts = ["Service post updated successfully."]
            if deleted_count > 0:
                success_parts.append(f"{deleted_count} image(s) deleted.")
            if uploaded_count > 0:
                success_parts.append(f"{uploaded_count} new image(s) added.")
            messages.success(self.request, " ".join(success_parts))
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
        return reverse_lazy("jobs:job_list") + "?tab=services"

# Optional function-based view for deactivating a post.
@login_required
def deactivate_service_post(request, slug):
    post = get_object_or_404(ServicePost, slug=slug, worker=request.user)
    post.is_active = False
    post.save()
    messages.info(request, "Service post has been deactivated.")
    return redirect("jobs:job_list")


# ============================================================================
# SERVICE REVIEW VIEWS (Rating & Comments with Moderation)
# ============================================================================

from django.http import JsonResponse
from django.db import IntegrityError
from .models import ServiceReview, ServiceReviewReport
from .forms import ServiceReviewForm, ServiceReviewReportForm


@login_required
def create_service_review(request, slug):
    """Create a new review for a service post"""
    service_post = get_object_or_404(ServicePost, slug=slug)
    
    # Check if user already reviewed this service
    existing_review = ServiceReview.objects.filter(
        service_post=service_post,
        reviewer=request.user
    ).first()
    
    if existing_review:
        messages.warning(request, "You have already reviewed this service. You can edit your existing review.")
        return redirect('services:servicepost_detail', slug=slug)
    
    if request.method == 'POST':
        form = ServiceReviewForm(request.POST)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.service_post = service_post
                review.reviewer = request.user
                
                # Check for banned words in comment
                is_flagged, flagged_words = check_for_banned_words(review.comment)
                
                if is_flagged:
                    review.is_flagged = True
                    review.flagged_words = ', '.join(flagged_words)
                    messages.warning(
                        request,
                        f"Your review contains inappropriate words: {', '.join(flagged_words)}. "
                        "It has been submitted but flagged for moderation."
                    )
                
                review.save()
                messages.success(request, "Your review has been posted successfully!")
                
            except IntegrityError:
                messages.error(request, "You have already reviewed this service.")
            
            return redirect('services:servicepost_detail', slug=slug)
    else:
        form = ServiceReviewForm()
    
    context = {
        'form': form,
        'service_post': service_post,
    }
    return render(request, 'services/review_form.html', context)


@login_required
def update_service_review(request, review_id):
    """Update an existing review"""
    review = get_object_or_404(ServiceReview, id=review_id, reviewer=request.user)
    service_post = review.service_post
    
    if request.method == 'POST':
        form = ServiceReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            
            # Re-check for banned words
            is_flagged, flagged_words = check_for_banned_words(review.comment)
            
            if is_flagged:
                review.is_flagged = True
                review.flagged_words = ', '.join(flagged_words)
                messages.warning(
                    request,
                    f"Your updated review contains inappropriate words: {', '.join(flagged_words)}. "
                    "It has been saved but flagged for moderation."
                )
            else:
                review.is_flagged = False
                review.flagged_words = ''
            
            review.save()
            messages.success(request, "Your review has been updated successfully!")
            return redirect('services:servicepost_detail', slug=service_post.slug)
    else:
        form = ServiceReviewForm(instance=review)
    
    context = {
        'form': form,
        'review': review,
        'service_post': service_post,
        'is_edit': True,
    }
    return render(request, 'services/review_form.html', context)


@login_required
def delete_service_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(ServiceReview, id=review_id, reviewer=request.user)
    service_post_slug = review.service_post.slug
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, "Your review has been deleted.")
        return redirect('services:servicepost_detail', slug=service_post_slug)
    
    context = {
        'review': review,
    }
    return render(request, 'services/review_confirm_delete.html', context)


@login_required
def report_service_review(request, review_id):
    """Report a review for inappropriate content"""
    review = get_object_or_404(ServiceReview, id=review_id)
    
    # Prevent self-reporting
    if review.reviewer == request.user:
        messages.error(request, "You cannot report your own review.")
        return redirect('services:servicepost_detail', slug=review.service_post.slug)
    
    # Check if user already reported this review
    existing_report = ServiceReviewReport.objects.filter(
        review=review,
        reporter=request.user
    ).first()
    
    if existing_report:
        messages.warning(request, "You have already reported this review.")
        return redirect('services:servicepost_detail', slug=review.service_post.slug)
    
    if request.method == 'POST':
        form = ServiceReviewReportForm(request.POST)
        if form.is_valid():
            try:
                report = form.save(commit=False)
                report.review = review
                report.reporter = request.user
                report.save()
                
                # Increment report count
                review.report_count += 1
                review.save()
                
                # Check for auto-removal (3+ reports from different users)
                if review.check_auto_removal():
                    messages.info(
                        request,
                        "This review has been automatically hidden due to multiple reports. "
                        "Our moderation team will review it."
                    )
                else:
                    messages.success(
                        request,
                        "Thank you for reporting this review. Our team will review it shortly."
                    )
                
            except IntegrityError:
                messages.error(request, "You have already reported this review.")
            
            return redirect('services:servicepost_detail', slug=review.service_post.slug)
    else:
        form = ServiceReviewReportForm()
    
    context = {
        'form': form,
        'review': review,
    }
    return render(request, 'services/review_report_form.html', context)


# Admin moderation view (only accessible to staff)
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def moderate_service_review(request, review_id):
    """Admin view to moderate a review"""
    review = get_object_or_404(ServiceReview, id=review_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        admin_notes = request.POST.get('admin_notes', '')
        
        if action == 'hide':
            review.is_hidden = True
            review.admin_notes = admin_notes
            review.save()
            messages.success(request, "Review has been hidden.")
        elif action == 'unhide':
            review.is_hidden = False
            review.admin_notes = admin_notes
            review.save()
            messages.success(request, "Review has been unhidden.")
        elif action == 'flag':
            review.is_flagged = True
            review.admin_notes = admin_notes
            review.save()
            messages.success(request, "Review has been flagged.")
        elif action == 'unflag':
            review.is_flagged = False
            review.admin_notes = admin_notes
            review.save()
            messages.success(request, "Review has been unflagged.")
        
        return redirect('services:servicepost_detail', slug=review.service_post.slug)
    
    context = {
        'review': review,
    }
    return render(request, 'services/review_moderate.html', context)
