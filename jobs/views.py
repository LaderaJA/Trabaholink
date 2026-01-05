import json
import re
from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from admin_dashboard.moderation_utils import check_for_banned_words
from notifications.models import Notification
from services.models import ServicePost

from .forms import ContractDraftForm, JobApplicationForm, JobForm, JobImageForm
from .models import (Contract, Feedback, Job, JobApplication, JobCategory,
                     JobImage, JobOffer, ProgressLog)
from .utils import get_users_who_applied


DEFAULT_CONTRACT_TERMS = (
    "1. Work will be performed according to the specifications outlined above.\n"
    "2. Payment will be made according to the agreed schedule.\n"
    "3. Any additional work outside the scope will require a new agreement.\n"
    "4. Intellectual property rights will be transferred upon final payment."
)


def normalize_contract_terms_text(text):
    if text is None:
        return ""

    normalized = text.replace('\r\n', '\n').replace('\r', '\n')
    normalized = normalized.replace('\\n', '\n')
    normalized = re.sub(r'<br\s*/?>', '\n', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'</p\s*>', '\n\n', normalized, flags=re.IGNORECASE)
    normalized = re.sub(r'<p[^>]*>', '', normalized, flags=re.IGNORECASE)
    normalized = normalized.replace('&nbsp;', ' ')
    # Collapse more than two consecutive newlines to two for readability
    normalized = re.sub(r'\n{3,}', '\n\n', normalized)
    return normalized.strip()
# Homepage View (Static Landing Page)
class HomePageView(TemplateView):
    template_name = "mainpages/home.html"

    def get_context_data(self, **kwargs):
        from django.contrib.auth import get_user_model
        from announcements.models import Announcement
        
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        now = timezone.now()
        
        # Get real statistics from database
        context["categories"] = JobCategory.objects.all()
        context["total_jobs"] = Job.objects.count()
        context["total_users"] = User.objects.count()
        # Count only active and non-expired jobs
        context["active_jobs"] = Job.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).count()
        
        # Get recent announcements for carousel
        context["announcements"] = Announcement.objects.all().order_by('-id')[:3]
        
        # Get recent jobs for display (active and non-expired only)
        context["recent_jobs"] = Job.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).order_by('-created_at')[:6]
        
        return context

# simple full address helper
def build_full_address(job):
    parts = filter(None, [
        job.house_number,
        job.street,
        job.subdivision,
        job.barangay,
        job.municipality,
    ])
    return ", ".join(parts)

@csrf_exempt
def set_user_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request.session['user_location'] = {
                'lat': data['lat'],
                'lng': data['lng']
            }
            return JsonResponse({'status': 'ok'})
        except (KeyError, ValueError):
            return JsonResponse({'status': 'error', 'message': 'Invalid data'})
    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP method'})

class JobListView(ListView):
    model = Job
    template_name = "jobs/job_list.html"
    context_object_name = "jobs"
    paginate_by = 9

    def get_queryset(self):
        # Filter for active jobs and exclude expired ones
        now = timezone.now()
        queryset = Job.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).select_related("category")
        request = self.request

        # Filters
        category_id = request.GET.get("category")
        keyword = request.GET.get("q")
        user_lat = request.GET.get("lat")
        user_lng = request.GET.get("lng")
        urgency = request.GET.get("urgency")
        barangay = request.GET.get("barangay")
        sort = request.GET.get("sort", "date_desc")  # Default: newest first

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Urgency filter - map from template values to model values
        if urgency:
            urgency_mapping = {
                'low': 'Flexible',
                'medium': 'Specific Date',
                'high': 'Urgent'
            }
            model_urgency = urgency_mapping.get(urgency)
            if model_urgency:
                queryset = queryset.filter(urgency=model_urgency)
        
        # Comprehensive keyword search across multiple fields
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(municipality__icontains=keyword) |
                Q(barangay__icontains=keyword) |
                Q(street__icontains=keyword) |
                Q(subdivision__icontains=keyword) |
                Q(category__name__icontains=keyword) |
                Q(required_skills__icontains=keyword) |
                Q(owner__first_name__icontains=keyword) |
                Q(owner__last_name__icontains=keyword)
            ).distinct()
        
        # Removed min_budget and max_budget filters (simplified UI)
        # Don't filter by location fields from the location modal
        # The modal sets municipality parameter only for distance calculation
        # Search form uses 'q' parameter which is already handled above
        # This prevents "No Jobs Found" when using location modal

        self.user_location = None
        # Handle GPS coordinates
        if user_lat and user_lng:
            try:
                self.user_location = Point(float(user_lng), float(user_lat), srid=4326)
                queryset = queryset.annotate(distance=Distance("location", self.user_location))
            except (ValueError, TypeError):
                self.user_location = None
        
        # Barangay filter (simple text search)
        if barangay:
            queryset = queryset.filter(barangay__icontains=barangay)

        # Sorting
        if sort == "budget_asc":
            queryset = queryset.order_by("budget")
        elif sort == "budget_desc":
            queryset = queryset.order_by("-budget")
        elif sort == "date_asc":
            queryset = queryset.order_by("created_at")
        elif sort == "distance" and self.user_location:
            queryset = queryset.order_by("distance")
        else:  
            queryset = queryset.order_by("-created_at")

        # Cache queryset and annotate full address + distance
        self._queryset = list(queryset)
        for job in self._queryset:
            job.full_address = build_full_address(job)
            job.distance_km = round(job.distance.km, 2) if hasattr(job, "distance") and job.distance else None
        return self._queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = JobCategory.objects.all()
        context["request"] = self.request
        context["user_location"] = getattr(self, 'user_location', None)

        # Use the already filtered jobs count (total after filtering)
        context["jobs_count"] = len(getattr(self, '_queryset', []))

        # Service filters based on ServicePost model fields
        service_filters = {"is_active": True}
        service_keyword = self.request.GET.get("q")
        service_category_id = self.request.GET.get("category")

        services_qs = ServicePost.objects.filter(**service_filters)

        # Keyword search in headline or description
        if service_keyword:
            services_qs = services_qs.filter(
                Q(headline__icontains=service_keyword) | Q(description__icontains=service_keyword)
            )

        # Instead of filtering location with __icontains (since 'location' is a PointField),
        # check if lat & lng are provided and annotate distance.
        user_lat = self.request.GET.get("lat")
        user_lng = self.request.GET.get("lng")
        if user_lat and user_lng:
            try:
                user_loc = Point(float(user_lng), float(user_lat), srid=4326)
                services_qs = services_qs.annotate(distance=Distance("location", user_loc))
                # Order by distance if needed (or leave the default ordering)
                services_qs = services_qs.order_by("distance")
            except (ValueError, TypeError):
                pass
        else:
            services_qs = services_qs.order_by("-created_at")

        if service_category_id:
            services_qs = services_qs.filter(category_id=service_category_id).distinct()

        services_qs = services_qs.order_by("-created_at")
        context["services"] = services_qs
        context["services_count"] = services_qs.count()

        # Capture active tab from URL (default to "jobs")
        context["active_tab"] = self.request.GET.get("tab", "jobs")

        return context

# 🔹 Job Detail View
class JobDetailView(DetailView):
    model = Job
    template_name = "jobs/job_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        job = self.get_object()
        user = self.request.user

        if user.is_authenticated:
            # Check if the user is the owner of the job
            context["is_owner"] = user == job.owner

            # Get the list of applicants if the user is the owner
            if context["is_owner"]:
                applicants = job.applications.select_related("worker").all()

                # Apply filters
                search_query = self.request.GET.get("search", "")
                if search_query:
                    applicants = applicants.filter(
                        Q(worker__username__icontains=search_query) |
                        Q(worker__first_name__icontains=search_query) |
                        Q(worker__last_name__icontains=search_query)
                    )

                # Paginate the applicants
                paginator = Paginator(applicants, 10)  # Show 10 applicants per page
                page_number = self.request.GET.get("page")
                page_obj = paginator.get_page(page_number)

                context["applicants"] = page_obj
                context["search_query"] = search_query

            # Check if the user has already applied for the job
            context["has_applied"] = job.applications.filter(worker=user).exists()
            
            # Check if user has uploaded CV (for workers)
            context["user_has_cv"] = bool(user.cv_file) if hasattr(user, 'cv_file') else False

        return context

# 🔹 Job Create View (with geolocation support)
class JobCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("jobs:job_list")
    
    def test_func(self):
        """Only clients can post jobs"""
        return self.request.user.role == 'client'
    
    def _get_precise_coordinates(self, municipality, barangay):
        """Get precise coordinates for specific barangay within a municipality."""
        if not municipality or not barangay:
            return None
            
        # Bacoor barangay coordinates (6 decimal places for precision)
        bacoor_barangays = {
            'molino': {'lat': 14.423512, 'lng': 120.982478},
            'molino 1': {'lat': 14.423512, 'lng': 120.982478},
            'molino 2': {'lat': 14.423512, 'lng': 120.982478},
            'molino 3': {'lat': 14.423512, 'lng': 120.982478},
            'molino 4': {'lat': 14.423512, 'lng': 120.982478},
            'molino 5': {'lat': 14.423512, 'lng': 120.982478},
            'molino 6': {'lat': 14.423512, 'lng': 120.982478},
            'molino 7': {'lat': 14.423512, 'lng': 120.982478},
            'queens row': {'lat': 14.440013, 'lng': 120.974982},
            'queens row central': {'lat': 14.440013, 'lng': 120.974982},
            'queens row east': {'lat': 14.440013, 'lng': 120.974982},
            'queens row west': {'lat': 14.440013, 'lng': 120.974982},
            'salawag': {'lat': 14.417528, 'lng': 120.954983},
            'springville': {'lat': 14.429045, 'lng': 120.991987},
            'panapaan': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 1': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 2': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 3': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 4': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 5': {'lat': 14.452013, 'lng': 120.968041},
            'tabing dagat': {'lat': 14.462015, 'lng': 120.959028},
            'mabolo': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 1': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 2': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 3': {'lat': 14.414987, 'lng': 120.969964},
            'niog': {'lat': 14.420019, 'lng': 120.960047},
            'niog 1': {'lat': 14.420019, 'lng': 120.960047},
            'niog 2': {'lat': 14.420019, 'lng': 120.960047},
            'niog 3': {'lat': 14.420019, 'lng': 120.960047},
            'zapote': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 1': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 2': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 3': {'lat': 14.434567, 'lng': 120.975432},
        }
        
        if municipality == 'bacoor' and barangay in bacoor_barangays:
            return bacoor_barangays[barangay]
        
        return None
    
    def _get_municipality_coordinates(self, municipality):
        """Get coordinates for municipality (fallback)."""
        municipalities = {
            'manila': {'lat': 14.599512, 'lng': 120.984222},
            'quezon city': {'lat': 14.676041, 'lng': 121.043700},
            'makati': {'lat': 14.554729, 'lng': 121.024445},
            'pasig': {'lat': 14.576417, 'lng': 121.085098},
            'taguig': {'lat': 14.517637, 'lng': 121.050935},
            'bacoor': {'lat': 14.431095, 'lng': 120.968096},
            'imus': {'lat': 14.429741, 'lng': 120.937028},
            'dasmarinas': {'lat': 14.400415, 'lng': 120.985887},
            'dasmariñas': {'lat': 14.400415, 'lng': 120.985887},
            'cavite city': {'lat': 14.479142, 'lng': 120.897897},
            'antipolo': {'lat': 14.593069, 'lng': 121.180027},
        }
        return municipalities.get(municipality)
    
    def handle_no_permission(self):
        """Redirect workers who try to post jobs"""
        messages.error(self.request, "Only clients can post jobs. Workers can apply to jobs instead.")
        return redirect('jobs:job_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_form'] = JobImageForm(self.request.POST, self.request.FILES)
        else:
            context['image_form'] = JobImageForm()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        image_form = context['image_form']

        # Check for banned words in title
        title = form.cleaned_data.get('title', '')
        description = form.cleaned_data.get('description', '')
        tasks = form.cleaned_data.get('tasks', '')
        
        is_flagged_title, flagged_words_title = check_for_banned_words(title)
        is_flagged_desc, flagged_words_desc = check_for_banned_words(description)
        is_flagged_tasks, flagged_words_tasks = check_for_banned_words(tasks)
        
        # Combine all flagged words
        all_flagged = set(flagged_words_title + flagged_words_desc + flagged_words_tasks)
        
        if all_flagged:
            messages.error(
                self.request,
                f"Your job post contains inappropriate words: {', '.join(all_flagged)}. Please remove them and try again."
            )
            return self.form_invalid(form)

        # Update Job object
        job = form.save(commit=False)
        job.owner = self.request.user

        # Enhanced location handling with barangay-level precision
        lat = self.request.POST.get("latitude")
        lng = self.request.POST.get("longitude")
        municipality = form.cleaned_data.get('municipality', '').lower().strip()
        barangay = form.cleaned_data.get('barangay', '').lower().strip()
        
        # Try to get precise coordinates from our database first
        coords = self._get_precise_coordinates(municipality, barangay)
        
        if coords:
            # Use our precise barangay-level coordinates
            job.location = Point(coords['lng'], coords['lat'], srid=4326)
            job.latitude = coords['lat']
            job.longitude = coords['lng']
        elif lat and lng:
            # Fallback to user-provided coordinates
            job.location = Point(float(lng), float(lat), srid=4326)
            job.latitude = float(lat)
            job.longitude = float(lng)
        else:
            # Last resort: use municipality-level coordinates
            muni_coords = self._get_municipality_coordinates(municipality)
            if muni_coords:
                job.location = Point(muni_coords['lng'], muni_coords['lat'], srid=4326)
                job.latitude = muni_coords['lat']
                job.longitude = muni_coords['lng']

        job.save()

        # Handle images
        files = self.request.FILES.getlist('images')
        if files:
            for f in files:
                JobImage.objects.create(job=job, image=f)

        messages.success(self.request, "Job posted successfully!")
        # Redirect to success URL
        return redirect(self.success_url)

# 🔹 Job Update View (Only job owners can edit)
class JobUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    
    def test_func(self):
        return self.request.user == self.get_object().owner
    
    def _get_precise_coordinates(self, municipality, barangay):
        """Get precise coordinates for specific barangay within a municipality."""
        if not municipality or not barangay:
            return None
            
        # Bacoor barangay coordinates (6 decimal places for precision)
        bacoor_barangays = {
            'molino': {'lat': 14.423512, 'lng': 120.982478},
            'molino 1': {'lat': 14.423512, 'lng': 120.982478},
            'molino 2': {'lat': 14.423512, 'lng': 120.982478},
            'molino 3': {'lat': 14.423512, 'lng': 120.982478},
            'molino 4': {'lat': 14.423512, 'lng': 120.982478},
            'molino 5': {'lat': 14.423512, 'lng': 120.982478},
            'molino 6': {'lat': 14.423512, 'lng': 120.982478},
            'molino 7': {'lat': 14.423512, 'lng': 120.982478},
            'queens row': {'lat': 14.440013, 'lng': 120.974982},
            'queens row central': {'lat': 14.440013, 'lng': 120.974982},
            'queens row east': {'lat': 14.440013, 'lng': 120.974982},
            'queens row west': {'lat': 14.440013, 'lng': 120.974982},
            'salawag': {'lat': 14.417528, 'lng': 120.954983},
            'springville': {'lat': 14.429045, 'lng': 120.991987},
            'panapaan': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 1': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 2': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 3': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 4': {'lat': 14.452013, 'lng': 120.968041},
            'panapaan 5': {'lat': 14.452013, 'lng': 120.968041},
            'tabing dagat': {'lat': 14.462015, 'lng': 120.959028},
            'mabolo': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 1': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 2': {'lat': 14.414987, 'lng': 120.969964},
            'mabolo 3': {'lat': 14.414987, 'lng': 120.969964},
            'niog': {'lat': 14.420019, 'lng': 120.960047},
            'niog 1': {'lat': 14.420019, 'lng': 120.960047},
            'niog 2': {'lat': 14.420019, 'lng': 120.960047},
            'niog 3': {'lat': 14.420019, 'lng': 120.960047},
            'zapote': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 1': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 2': {'lat': 14.434567, 'lng': 120.975432},
            'zapote 3': {'lat': 14.434567, 'lng': 120.975432},
        }
        
        if municipality == 'bacoor' and barangay in bacoor_barangays:
            return bacoor_barangays[barangay]
        
        return None
    
    def _get_municipality_coordinates(self, municipality):
        """Get coordinates for municipality (fallback)."""
        municipalities = {
            'manila': {'lat': 14.599512, 'lng': 120.984222},
            'quezon city': {'lat': 14.676041, 'lng': 121.043700},
            'makati': {'lat': 14.554729, 'lng': 121.024445},
            'pasig': {'lat': 14.576417, 'lng': 121.085098},
            'taguig': {'lat': 14.517637, 'lng': 121.050935},
            'bacoor': {'lat': 14.431095, 'lng': 120.968096},
            'imus': {'lat': 14.429741, 'lng': 120.937028},
            'dasmarinas': {'lat': 14.400415, 'lng': 120.985887},
            'dasmariñas': {'lat': 14.400415, 'lng': 120.985887},
            'cavite city': {'lat': 14.479142, 'lng': 120.897897},
            'antipolo': {'lat': 14.593069, 'lng': 121.180027},
        }
        return municipalities.get(municipality)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_form'] = JobImageForm(self.request.POST, self.request.FILES)
        else:
            context['image_form'] = JobImageForm()
        context['existing_images'] = self.object.jobimage_set.all()
        return context
    
    def form_valid(self, form):
        # Check for banned words in title
        title = form.cleaned_data.get('title', '')
        description = form.cleaned_data.get('description', '')
        tasks = form.cleaned_data.get('tasks', '')
        
        is_flagged_title, flagged_words_title = check_for_banned_words(title)
        is_flagged_desc, flagged_words_desc = check_for_banned_words(description)
        is_flagged_tasks, flagged_words_tasks = check_for_banned_words(tasks)
        
        # Combine all flagged words
        all_flagged = set(flagged_words_title + flagged_words_desc + flagged_words_tasks)
        
        if all_flagged:
            messages.error(
                self.request,
                f"Your job post contains inappropriate words: {', '.join(all_flagged)}. Please remove them and try again."
            )
            return self.form_invalid(form)
        
        # Enhanced location handling with barangay-level precision
        lat = self.request.POST.get("latitude")
        lng = self.request.POST.get("longitude")
        municipality = form.cleaned_data.get('municipality', '').lower().strip()
        barangay = form.cleaned_data.get('barangay', '').lower().strip()
        
        # Try to get precise coordinates from our database first
        coords = self._get_precise_coordinates(municipality, barangay)
        
        if coords:
            # Use our precise barangay-level coordinates
            form.instance.location = Point(coords['lng'], coords['lat'], srid=4326)
            form.instance.latitude = coords['lat']
            form.instance.longitude = coords['lng']
        elif lat and lng:
            # Fallback to user-provided coordinates
            form.instance.location = Point(float(lng), float(lat), srid=4326)
            form.instance.latitude = float(lat)
            form.instance.longitude = float(lng)
        else:
            # Last resort: use municipality-level coordinates
            muni_coords = self._get_municipality_coordinates(municipality)
            if muni_coords:
                form.instance.location = Point(muni_coords['lng'], muni_coords['lat'], srid=4326)
                form.instance.latitude = muni_coords['lat']
                form.instance.longitude = muni_coords['lng']
        
        response = super().form_valid(form)
        
        # Handle image deletions
        delete_image_ids = self.request.POST.getlist('delete_image')
        if delete_image_ids:
            for image_id in delete_image_ids:
                try:
                    image = JobImage.objects.get(id=image_id, job=self.object)
                    image.delete()
                except JobImage.DoesNotExist:
                    pass
        
        # Handle new image uploads
        files = self.request.FILES.getlist('images')
        if files:
            for img in files:
                JobImage.objects.create(job=self.object, image=img)
        
        messages.success(self.request, "Job updated successfully!")
        return response
    
    def get_success_url(self):
        return reverse_lazy("jobs:job_detail", kwargs={"pk": self.object.pk})
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'delete_image' in request.POST:
            image_id = request.POST.get('delete_image')
            try:
                image = JobImage.objects.get(id=image_id)
                # Check if the image belongs to a job owned by the current user
                if image.job.owner == request.user:
                    image.delete()
                    return JsonResponse({"status": "success"})
                else:
                    return JsonResponse({"status": "error", "message": "Permission denied."})
            except JobImage.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Image not found."})
        
        # If not an AJAX request, handle normal form submission
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)
# 🔹 Job Delete View
class JobDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Job
    template_name = "jobs/job_confirm_delete.html"
    success_url = reverse_lazy("jobs:job_list")

    def test_func(self):
        return self.request.user == self.get_object().owner

# 🔹 Job Application View
class JobApplicationCreateView(LoginRequiredMixin, CreateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = "jobs/job_application_form.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has already applied to this job
        job = get_object_or_404(Job, pk=self.kwargs.get("pk"))
        existing_application = JobApplication.objects.filter(
            job=job,
            worker=request.user
        ).first()
        
        if existing_application:
            messages.warning(request, "You have already applied to this job.")
            return redirect(reverse("jobs:job_detail", kwargs={"pk": job.pk}))
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        application = form.save(commit=False)
        # Set the job from URL kwargs (the URL uses <int:pk>)
        application.job = get_object_or_404(Job, pk=self.kwargs.get("pk"))
        application.worker = self.request.user
        
        # Handle CV attachment checkbox
        attach_cv = self.request.POST.get('attach_cv') == 'on'
        application.attach_profile_cv = attach_cv
        
        # Double-check for duplicate (race condition protection)
        existing = JobApplication.objects.filter(
            job=application.job,
            worker=application.worker
        ).first()
        
        if existing:
            messages.warning(self.request, "You have already applied to this job.")
            return redirect(reverse("jobs:job_detail", kwargs={"pk": application.job.id}))
        
        application.save()
        
        # Create notification for job owner
        Notification.objects.create(
            user=application.job.owner,
            message=f"{application.worker.get_full_name() or application.worker.username} applied for '{application.job.title}'",
            notif_type="job_application",
            object_id=application.pk,
        )
        
        messages.success(self.request, "Your application has been submitted successfully!")
        return redirect(reverse("jobs:job_detail", kwargs={"pk": application.job.id}))

class JobApplicationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = "jobs/job_application_form.html"
    
    def form_valid(self, form):
        application = form.save(commit=False)
        application.save()
        return redirect(reverse("jobs:job_detail", kwargs={"id": application.job.id}))

    def test_func(self):
        application = self.get_object()
        # Allow only the applicant (or job owner) to update
        return self.request.user == application.worker or self.request.user == application.job.owner

# 🔹 Contract Detail View
class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = "jobs/contract_detail.html"
    context_object_name = "contract"
    http_method_names = ["get", "post", "head", "options"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object
        context['progress_logs'] = contract.progress_logs.all().order_by('-timestamp')
        context['default_contract_terms'] = DEFAULT_CONTRACT_TERMS
        terms_source = contract.terms or DEFAULT_CONTRACT_TERMS
        normalized_terms = normalize_contract_terms_text(terms_source)
        final_terms = normalized_terms or DEFAULT_CONTRACT_TERMS
        context['contract_terms_text'] = final_terms
        context['contract_terms_html'] = mark_safe(
            escape(final_terms).replace('\n', '<br>')
        )

        history_entries = []
        field_labels = {
            "job_title": "Job Title",
            "job_description": "Job Description",
            "agreed_rate": "Agreed Rate",
            "rate_type": "Rate Type",
            "payment_schedule": "Payment Schedule",
            "duration": "Duration",
            "schedule": "Schedule",
            "start_date": "Start Date",
            "end_date": "End Date",
            "notes": "Additional Notes",
            "terms": "Terms & Conditions",
        }

        history_queryset = (
            contract.history.select_related("history_user")
            .order_by("-history_date")
        )

        for record in history_queryset[:10]:
            prev_record = getattr(record, "prev_record", None)
            changes = []
            if prev_record:
                for field, label in field_labels.items():
                    old_value = getattr(prev_record, field, None)
                    new_value = getattr(record, field, None)
                    if old_value != new_value:
                        changes.append({
                            "field": label,
                            "old": self._format_history_value(old_value),
                            "new": self._format_history_value(new_value),
                        })

            history_entries.append({
                "user": record.history_user,
                "role": self._get_history_role(record.history_user, contract),
                "timestamp": record.history_date,
                "changes": changes,
                "type": record.history_type,
            })

        context["history_entries"] = history_entries
        return context

    @staticmethod
    def _format_history_value(value):
        if value in (None, ""):
            return "Not specified"
        if isinstance(value, (date, datetime)):
            return value.strftime("%B %d, %Y")
        if isinstance(value, Decimal):
            return f"₱{value:,.2f}"
        if isinstance(value, str):
            return value.replace('\r\n', '\n').replace('\r', '\n').replace('\\n', '\n')
        return str(value)

    @staticmethod
    def _get_history_role(user, contract):
        if not user:
            return "System"
        if user == contract.client:
            return "Client"
        if user == contract.worker:
            return "Worker"
        return "User"

# Standalone image deletion view 
@csrf_exempt
def delete_image(request):
    if request.method == "POST":
        # Check if the request is an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            image_id = request.POST.get('delete_image')
            try:
                image = JobImage.objects.get(id=image_id)
                # Check if the image belongs to a job owned by the current user
                if image.job.owner == request.user:
                    image.delete()
                    return JsonResponse({'status': 'success', 'message': 'Image deleted successfully'})
                else:
                    return JsonResponse({'status': 'error', 'message': 'Permission denied'})
            except JobImage.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Image not found'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid request type'})
    return JsonResponse({'status': 'error', 'message': 'Invalid HTTP method'})



def job_applicants_view(request, job_id):
    users = get_users_who_applied(job_id)
    user_data = [{"id": user.id, "username": user.username, "email": user.email} for user in users]
    return JsonResponse({"applicants": user_data})



def deny_application(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)
    if request.user == application.job.owner:
        application.delete()
    return HttpResponseRedirect(reverse('jobs:job_detail', kwargs={'pk': application.job.pk}))



# Job Application Detail View (viewable by everyone)
class JobApplicationDetailView(LoginRequiredMixin, DetailView):
    model = JobApplication
    template_name = "jobs/job_application_detail.html"
    context_object_name = "application"
    
    def get_object(self):
        obj = super().get_object()
        # Mark as viewed if employer is viewing
        if self.request.user == obj.job.owner:
            obj.mark_as_viewed()
        return obj
    
    def get_queryset(self):
        return JobApplication.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from messaging.models import Conversation, Message
        from django.db.models import Q
        
        application = self.get_object()
        
        # Find conversation between employer and worker
        # Conversation can be either user1-user2 or user2-user1
        conversation = Conversation.objects.filter(
            Q(user1=application.job.owner, user2=application.worker) |
            Q(user1=application.worker, user2=application.job.owner)
        ).first()
        
        print(f"DEBUG: Application ID: {application.id}")
        print(f"DEBUG: Job Owner: {application.job.owner.username}")
        print(f"DEBUG: Worker: {application.worker.username}")
        print(f"DEBUG: Conversation found: {conversation}")
        
        if conversation:
            messages_list = list(conversation.messages.order_by('created_at'))
            print(f"DEBUG: Messages count: {len(messages_list)}")
            context['conversation'] = conversation
            context['conversation_messages'] = messages_list
        else:
            print("DEBUG: No conversation found")
            context['conversation'] = None
            context['conversation_messages'] = []
        
        return context

# Job Application Update View (only the applicant can edit)
class JobApplicationUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = "jobs/job_application_form.html"
    
    def test_func(self):
        application = self.get_object()
        return self.request.user == application.worker  # Only the applicant can update
    
    def get_success_url(self):
        return reverse_lazy("jobs:job_detail", kwargs={"pk": self.get_object().job.pk})

# Job Application Delete View (applicant or job owner can delete)
class JobApplicationDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = JobApplication
    template_name = "jobs/job_application_confirm_delete.html"
    
    def test_func(self):
        application = self.get_object()
        # Allowed if the logged-in user is either the applicant or the job owner
        return self.request.user == application.worker or self.request.user == application.job.owner
    
    def get_success_url(self):
        return reverse_lazy("jobs:job_detail", kwargs={"pk": self.get_object().job.pk})

# Job Application Hire View
class JobApplicationHireView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(JobApplication, pk=pk)
        if request.user != application.job.owner:
            messages.error(request, "You do not have permission to hire for this job.")
            return redirect(
                reverse("jobs:job_application_detail", kwargs={"pk": application.pk})
            )
        
        application.status = "Accepted"
        application.save()
        
        contract = Contract.objects.create(
            job=application.job,
            worker=application.worker,
            client=application.job.owner,
            application=application,
            status="Negotiation",
            start_date=timezone.now().date(),
            is_draft=True,
            job_title=application.job.title,
            job_description=application.job.description,
            payment_schedule=application.job.payment_schedule or "End of Project",
            duration=application.job.duration or "To be determined",
            schedule=application.job.schedule or "To be determined",
        )

        # Use the proper link for negotiation draft edit
        contract_url = reverse("jobs:contract_draft_edit", kwargs={"pk": contract.pk})

        Notification.objects.create(
            user=application.worker,
            message=f"Your application for '{application.job.title}' has been accepted. Click to negotiate: {contract_url}",
            notif_type="contract_draft_update",  # Changed type
            object_id=contract.pk,
        )
        
        messages.success(
            request, "Application accepted. Please negotiate and finalize the contract."
        )
        return redirect(reverse("jobs:contract_draft_edit", kwargs={"pk": contract.pk}))
    
    def test_func(self):
        application = get_object_or_404(JobApplication, pk=self.kwargs["pk"])
        return self.request.user == application.job.owner

class JobApplicationDenyView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(JobApplication, pk=pk)
        application.status = "Rejected"
        application.save()
        messages.info(request, "Application has been denied.")
        return redirect(reverse("jobs:job_application_detail", kwargs={"pk": application.pk}))

    def test_func(self):
        application = get_object_or_404(JobApplication, pk=self.kwargs["pk"])
        return self.request.user == application.job.owner

class ContractUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Contract
    fields = ['status', 'payment_status', 'is_revision_requested', 'feedback_by_client', 'rating_by_client', 'feedback_by_worker', 'start_date', 'end_date']
    template_name = "jobs/contract_form.html"
    
    def test_func(self):
        contract = self.get_object()
        return self.request.user == contract.client or self.request.user == contract.worker
    
    def get_success_url(self):
        return reverse_lazy("jobs:contract_detail", kwargs={"pk": self.object.pk})
    
# Draft contract update view
class ContractDraftUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Contract
    form_class = ContractDraftForm
    template_name = "jobs/contract_draft_form.html"

    def dispatch(self, request, *args, **kwargs):
        contract = self.get_object()
        
        # Check if contract is still in draft
        if not contract.is_draft:
            messages.warning(request, "This contract has been finalized and can no longer be edited.")
            return redirect("jobs:contract_detail", pk=contract.pk)
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Check if this is an AJAX request (auto-save)
        is_ajax = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        response = super().form_valid(form)
        self.object.history_user = self.request.user
        self.object.save()
        
        # Only show message and notify for manual saves, not auto-saves
        if not is_ajax:
            messages.success(self.request, "Contract draft has been updated successfully!")
            
            # Notify the other party
            if self.request.user == self.object.client:
                Notification.objects.create(
                    user=self.object.worker,
                    message=f"The client has updated the contract draft for '{self.object.job.title}'. Please review the changes.",
                    notif_type="contract_updated",
                    object_id=self.object.pk
                )
            else:
                Notification.objects.create(
                    user=self.object.client,
                    message=f"The worker has updated the contract draft for '{self.object.job.title}'. Please review the changes.",
                    notif_type="contract_updated",
                    object_id=self.object.pk
                )
        
        # Return JSON response for AJAX requests
        if is_ajax:
            from django.http import JsonResponse
            return JsonResponse({'status': 'success', 'message': 'Draft saved'})
        
        return response

    def form_invalid(self, form):
        # Return JSON response for AJAX requests
        is_ajax = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if is_ajax:
            from django.http import JsonResponse
            return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("jobs:contract_detail", kwargs={"pk": self.object.pk})

    def test_func(self):
        contract = self.get_object()
        return self.request.user == contract.client or self.request.user == contract.worker
    
    def handle_no_permission(self):
        messages.error(self.request, "You are not authorized to edit this contract.")
        return redirect("jobs:contract_detail", pk=self.kwargs.get('pk'))



@login_required
@require_POST
def finalize_contract(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    
    # Check if this is for draft finalization or final contract finalization
    if contract.is_draft:
        # Allow only involved parties to finalize draft
        if request.user != contract.client and request.user != contract.worker:
            messages.error(request, "You are not authorized to finalize this contract.")
            return redirect("jobs:contract_detail", pk=pk)
        
        # Finalize the contract: switch draft off and update status
        contract.finalize_contract()
        messages.success(request, "Contract finalized successfully! Both parties can now review and accept the contract.")
        
        # Notify the other party
        if request.user == contract.client:
            Notification.objects.create(
                user=contract.worker,
                message=f"The client has finalized the contract for '{contract.job.title}'. Please review and accept the contract.",
                notif_type="contract_finalized",
                object_id=contract.pk
            )
        else:
            Notification.objects.create(
                user=contract.client,
                message=f"The worker has finalized the contract for '{contract.job.title}'. Please review and accept the contract.",
                notif_type="contract_finalized",
                object_id=contract.pk
            )
    else:
        # Final contract finalization (after both parties accepted) - only client can do this
        if request.user != contract.client:
            messages.error(request, "Only the client can finalize the contract.")
            return redirect("jobs:contract_detail", pk=pk)
        
        # Check if both parties have accepted
        if not (contract.client_accepted and contract.worker_accepted):
            messages.error(request, "Both parties must accept the contract before it can be finalized.")
            return redirect("jobs:contract_detail", pk=pk)
        
        # Check if already finalized
        if hasattr(contract, 'is_finalized') and contract.is_finalized:
            messages.warning(request, "This contract has already been finalized.")
            return redirect("jobs:contract_detail", pk=pk)
        
        # Mark as finalized
        contract.is_finalized = True
        # Normalize terms before persisting so both detail and history views render cleanly
        contract.terms = normalize_contract_terms_text(contract.terms) or DEFAULT_CONTRACT_TERMS
        contract.save()
        
        messages.success(request, "Contract has been finalized! The worker can now start work.")
        
        # Notify worker
        Notification.objects.create(
            user=contract.worker,
            message=f"The contract for '{contract.job.title}' has been finalized by the client. You can now start work!",
            notif_type="contract_finalized",
            object_id=contract.pk
        )
    
    return redirect("jobs:contract_detail", pk=contract.pk)

@login_required
@require_POST
def cancel_contract(request, pk):
    contract = get_object_or_404(Contract, pk=pk)
    # Only the client may cancel the contract
    if request.user != contract.client:
        messages.error(request, "You are not authorized to cancel this contract.")
        return redirect("jobs:contract_detail", pk=pk)
    
    # Store the old status before changing it
    old_status = contract.status
    
    # Update the contract status to 'Cancelled'
    contract.status = "Cancelled"
    contract.is_draft = False  # Finalize cancellation if it was in draft
    contract.updated_at = timezone.now()
    contract.save()
    
    # If contract was finalized, increment vacancy to reopen position
    if old_status in ['Finalized', 'In Progress', 'Awaiting Review']:
        contract.job.increment_vacancy()
    
    # Notify the worker about the cancellation
    Notification.objects.create(
        user=contract.worker,
        message=f"The contract for '{contract.job.title}' has been cancelled by the employer.",
        notif_type="contract_cancelled",
        object_id=contract.pk
    )
    
    messages.success(request, "Contract cancelled successfully.")
    return redirect("jobs:contract_detail", pk=contract.pk)

@login_required
@require_POST
def reactivate_job(request, pk):
    """Reactivate a deactivated job posting"""
    job = get_object_or_404(Job, pk=pk)
    
    # Only the job owner can reactivate
    if request.user != job.owner:
        messages.error(request, "You are not authorized to reactivate this job.")
        return redirect("jobs:employer_dashboard")
    
    # Check if job is expired
    if job.is_expired():
        messages.error(request, "Cannot reactivate an expired job. Please edit the job to extend its expiration date.")
        return redirect("jobs:job_edit", pk=pk)
    
    # Check if job has vacancies
    if job.vacancies == 0:
        messages.error(request, "Cannot reactivate a job with 0 vacancies. Please edit the job to add more positions.")
        return redirect("jobs:job_edit", pk=pk)
    
    # Reactivate the job
    job.is_active = True
    job.save(update_fields=['is_active', 'updated_at'])
    
    messages.success(request, f"Job '{job.title}' has been successfully reactivated!")
    return redirect("jobs:employer_dashboard")

class ContractSignView(LoginRequiredMixin, DetailView):
    """
    View for signing a contract with signature pad
    """
    model = Contract
    template_name = "jobs/contract_sign.html"
    context_object_name = "contract"
    
    def get_queryset(self):
        # Only allow client or worker to access
        return Contract.objects.filter(
            Q(client=self.request.user) | Q(worker=self.request.user)
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.get_object()
        
        # Determine if user has already signed
        if self.request.user == contract.client:
            context['already_signed'] = contract.client_accepted
            context['user_role'] = 'client'
        elif self.request.user == contract.worker:
            context['already_signed'] = contract.worker_accepted
            context['user_role'] = 'worker'
        
        return context
    
    def post(self, request, *args, **kwargs):
        contract = self.get_object()
        signature_data = request.POST.get('signature', '')
        
        # Validate user authorization
        if request.user not in [contract.client, contract.worker]:
            messages.error(request, "You are not authorized to sign this contract.")
            return redirect("jobs:contract_detail", pk=contract.pk)
        
        # Check if already signed
        if request.user == contract.client and contract.client_accepted:
            messages.info(request, "You have already signed this contract.")
            return redirect("jobs:contract_detail", pk=contract.pk)
        
        if request.user == contract.worker and contract.worker_accepted:
            messages.info(request, "You have already signed this contract.")
            return redirect("jobs:contract_detail", pk=contract.pk)
        
        # Mark as signed
        if request.user == contract.client:
            contract.client_accepted = True
            messages.success(request, "You have successfully signed the contract as the client.")
        elif request.user == contract.worker:
            contract.worker_accepted = True
            messages.success(request, "You have successfully signed the contract as the worker.")
        
        contract.save()
        
        # Check if both parties have signed
        if contract.client_accepted and contract.worker_accepted:
            contract.finalize_contract()
            messages.success(request, "Contract has been finalized! Both parties have signed.")
            
            # Decrement job vacancy
            if contract.job.decrement_vacancy():
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Job {contract.job.id} vacancy decremented. Remaining: {contract.job.vacancies}")
            
            # Create notifications
            Notification.objects.create(
                user=contract.client,
                message=f"Contract for '{contract.job.title}' has been finalized. Work can now begin.",
                notif_type="contract_finalized",
                object_id=contract.pk
            )
            Notification.objects.create(
                user=contract.worker,
                message=f"Contract for '{contract.job.title}' has been finalized. You can now start work.",
                notif_type="contract_finalized",
                object_id=contract.pk
            )
        else:
            # Notify the other party
            if request.user == contract.client:
                Notification.objects.create(
                    user=contract.worker,
                    message=f"The client has signed the contract for '{contract.job.title}'. Please review and sign.",
                    notif_type="contract_signature",
                    object_id=contract.pk
                )
            else:
                Notification.objects.create(
                    user=contract.client,
                    message=f"The worker has signed the contract for '{contract.job.title}'. Please review and sign.",
                    notif_type="contract_signature",
                    object_id=contract.pk
                )
        
        return redirect("jobs:contract_detail", pk=contract.pk)


@login_required
@require_POST
def accept_contract(request, pk):
    """Accept contract with confirmation (no e-sign)"""
    contract = get_object_or_404(Contract, pk=pk)
    
    # Validate user authorization
    if request.user not in [contract.client, contract.worker]:
        messages.error(request, "You are not authorized to access this contract.")
        return redirect("jobs:contract_detail", pk=pk)
    
    # Check if already accepted
    if request.user == contract.client and contract.client_accepted:
        messages.info(request, "You have already accepted this contract.")
        return redirect("jobs:contract_detail", pk=pk)
    
    if request.user == contract.worker and contract.worker_accepted:
        messages.info(request, "You have already accepted this contract.")
        return redirect("jobs:contract_detail", pk=pk)
    
    # Mark as accepted
    if request.user == contract.client:
        contract.client_accepted = True
        messages.success(request, "You have successfully accepted the contract as the client.")
    elif request.user == contract.worker:
        contract.worker_accepted = True
        messages.success(request, "You have successfully accepted the contract as the worker.")
    
    contract.save()
    
    # Check if both parties have accepted
    if contract.client_accepted and contract.worker_accepted:
        messages.success(request, "Both parties have accepted! The client can now finalize the contract.")
        
        # Notify both parties
        Notification.objects.create(
            user=contract.client,
            message=f"Both parties have accepted the contract for '{contract.job.title}'. You can now finalize it to allow work to begin.",
            notif_type="contract_accepted",
            object_id=contract.pk
        )
        Notification.objects.create(
            user=contract.worker,
            message=f"Both parties have accepted the contract for '{contract.job.title}'. Waiting for client to finalize.",
            notif_type="contract_accepted",
            object_id=contract.pk
        )
    else:
        # Notify the other party
        if request.user == contract.client:
            Notification.objects.create(
                user=contract.worker,
                message=f"The client has accepted the contract for '{contract.job.title}'. Please review and accept.",
                notif_type="contract_signature",
                object_id=contract.pk
            )
        else:
            Notification.objects.create(
                user=contract.client,
                message=f"The worker has accepted the contract for '{contract.job.title}'. Please review and accept.",
                notif_type="contract_signature",
                object_id=contract.pk
            )
    
    return redirect("jobs:contract_detail", pk=contract.pk)


# ============================================
# DASHBOARD VIEWS
# ============================================

class EmployerDashboardView(LoginRequiredMixin, TemplateView):
    """
    Comprehensive employer dashboard showing jobs, applications, offers, and contracts
    Only accessible to users who have posted at least one job
    """
    template_name = "jobs/employer_dashboard.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has posted any jobs
        if not Job.objects.filter(owner=request.user).exists():
            messages.info(request, "You need to post a job first to access the employer dashboard.")
            return redirect('jobs:job_create')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get all user's jobs for filtering
        context['user_jobs'] = Job.objects.filter(owner=user).order_by('-created_at')
        
        # Statistics
        context['total_jobs'] = Job.objects.filter(owner=user).count()
        context['active_jobs'] = Job.objects.filter(owner=user, is_active=True).count()
        context['deactivated_jobs_count'] = Job.objects.filter(owner=user, is_active=False).count()
        # Total applications should count only Pending applications (those needing review)
        context['total_applications'] = JobApplication.objects.filter(job__owner=user, status='Pending').count()
        context['pending_applications'] = JobApplication.objects.filter(
            job__owner=user, 
            status='Pending'
        ).count()
        context['rejected_applications'] = JobApplication.objects.filter(
            job__owner=user,
            status__iexact='rejected'
        ).count()
        context['active_contracts'] = Contract.objects.filter(
            client=user
        ).exclude(status__in=['Completed', 'Cancelled']).count()
        context['completed_contracts'] = Contract.objects.filter(
            client=user, 
            status='Completed'
        ).count()
        context['cancelled_contracts'] = Contract.objects.filter(
            client=user,
            status='Cancelled'
        ).count()
        
        # Recent jobs
        context['recent_jobs'] = Job.objects.filter(owner=user).order_by('-created_at')[:5]
        
        # Deactivated jobs (auto-deactivated when all positions filled or expired)
        context['deactivated_jobs'] = Job.objects.filter(
            owner=user,
            is_active=False
        ).select_related('category').order_by('-updated_at')[:50]
        
        # Recent applications shown in Applications tab (exclude ones already under contracts)
        # Note: Only exclude applications that THEMSELVES have active/completed contracts,
        # not applications to jobs that have contracts with OTHER workers
        recent_applications_qs = JobApplication.objects.filter(
            job__owner=user
        ).exclude(
            status__iexact='rejected'
        ).exclude(
            status__iexact='archived'
        ).filter(
            Q(contract__isnull=True) | 
            ~Q(contract__status__in=['Negotiation', 'Finalized', 'In Progress', 'Awaiting Review', 'Completed'])
        ).select_related('job', 'worker', 'offer', 'contract').order_by('-applied_at')[:50]
        context['recent_applications'] = recent_applications_qs
        context['applications_tab_count'] = recent_applications_qs.count()
        
        # Rejected applications list
        context['rejected_applications_list'] = JobApplication.objects.filter(
            job__owner=user,
            status__iexact='rejected'
        ).select_related('job', 'worker').order_by('-updated_at')[:50]
        
        # Pending offers
        context['pending_offers'] = JobOffer.objects.filter(
            employer=user,
            status='Pending'
        ).select_related('job', 'worker')[:5]
        
        # Active contracts
        context['active_contracts_list'] = Contract.objects.filter(
            client=user,
            status__in=['Negotiation', 'Finalized', 'Accepted', 'In Progress', 'Awaiting Review']
        ).select_related('job', 'worker').order_by('-created_at')[:50]
        context['completed_contracts_list'] = Contract.objects.filter(
            client=user,
            status='Completed'
        ).select_related('job', 'worker').order_by('-updated_at')[:50]
        context['cancelled_contracts_list'] = Contract.objects.filter(
            client=user,
            status='Cancelled'
        ).select_related('job', 'worker').order_by('-updated_at')[:50]
        
        return context


class WorkerDashboardView(LoginRequiredMixin, TemplateView):
    """
    Comprehensive worker dashboard showing applications, offers, and contracts
    Only accessible to users who have applied to at least one job
    """
    template_name = "jobs/worker_dashboard.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has applied to any jobs
        if not JobApplication.objects.filter(worker=request.user).exists():
            messages.info(request, "You need to apply to a job first to access the worker dashboard.")
            return redirect('jobs:job_list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Statistics
        context['total_applications'] = JobApplication.objects.filter(worker=user).exclude(status__iexact='Archived').count()
        context['pending_applications'] = JobApplication.objects.filter(
            worker=user, 
            status='Pending'
        ).count()
        context['active_contracts'] = Contract.objects.filter(worker=user).exclude(status__in=['Completed', 'Cancelled']).count()
        context['completed_contracts'] = Contract.objects.filter(
            worker=user, 
            status='Completed'
        ).count()
        context['cancelled_contracts'] = Contract.objects.filter(
            worker=user,
            status='Cancelled'
        ).count()
        
        # Recent applications
        recent_applications_qs = JobApplication.objects.filter(
            worker=user
        ).exclude(
            status__iexact='archived'
        ).exclude(
            contract__status__in=['Negotiation', 'Finalized', 'In Progress', 'Awaiting Review', 'Completed']
        ).select_related('job', 'contract').order_by('-applied_at')[:10]
        context['recent_applications'] = recent_applications_qs
        context['applications_tab_count'] = recent_applications_qs.count()
        
        # Pending offers
        context['pending_offers'] = JobOffer.objects.filter(
            worker=user,
            status='Pending'
        ).select_related('job', 'employer')[:5]
        
        # Active contracts
        context['active_contracts_list'] = Contract.objects.filter(
            worker=user,
            status__in=['Negotiation', 'Finalized', 'Accepted', 'In Progress', 'Awaiting Review']
        ).select_related('job', 'client').order_by('-updated_at')[:50]
        context['completed_contracts_list'] = Contract.objects.filter(
            worker=user,
            status='Completed'
        ).select_related('job', 'client').order_by('-updated_at')[:50]
        context['cancelled_contracts_list'] = Contract.objects.filter(
            worker=user,
            status='Cancelled'
        ).select_related('job', 'client').order_by('-updated_at')[:50]
        
        # Available jobs (nearby) - exclude user's own jobs and jobs already applied to
        now = timezone.now()
        context['available_jobs'] = Job.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        ).exclude(
            owner=user  # Exclude user's own jobs
        ).exclude(
            applications__worker=user  # Exclude jobs already applied to
        ).order_by('-created_at')[:10]
        
        # Calendar and schedule data
        from .schedule_utils import get_upcoming_deadlines
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        context['upcoming_deadlines'] = get_upcoming_deadlines(user.id, days_ahead=7)
        context['today'] = today.isoformat()
        
        # Get contracts with dates for initial calendar view
        scheduled_contracts = Contract.objects.filter(
            worker=user,
            status__in=['Accepted', 'In Progress', 'Finalized', 'Awaiting Review'],
            start_date__isnull=False
        ).select_related('job', 'client').order_by('start_date')[:20]
        context['scheduled_contracts'] = scheduled_contracts
        
        return context


# DEPRECATED: Old offer system - use new workflow instead
# class JobOfferDetailView(LoginRequiredMixin, DetailView):
#     """View for job offer details"""
#     model = JobOffer
#     template_name = "jobs/job_offer_detail.html"
#     context_object_name = "offer"
#     
#     def get_queryset(self):
#         # Only show offers user is involved in
#         return JobOffer.objects.filter(
#             Q(employer=self.request.user) | Q(worker=self.request.user)
#         )



# DEPRECATED: Old offer system - use new workflow instead
# @login_required
# @require_POST
# def accept_job_offer(request, pk):
#     """Accept a job offer"""
#     offer = get_object_or_404(JobOffer, pk=pk)
#     
#     if offer.worker != request.user:
#         messages.error(request, "You are not authorized to accept this offer.")
#         return redirect("jobs:job_offer_detail", pk=pk)
#     
#     if offer.status != "Pending":
#         messages.error(request, "This offer is no longer available.")
#         return redirect("jobs:job_offer_detail", pk=pk)
#     
#     if offer.is_expired():
#         messages.error(request, "This offer has expired.")
#         return redirect("jobs:job_offer_detail", pk=pk)
#     
#     # Accept the offer
#     offer.accept_offer()
#     
#     # Send notification to employer with link to contract draft
#     Notification.objects.create(
#         user=offer.employer,
#         message=f"{offer.worker.username} accepted your offer for '{offer.job.title}'! Click to negotiate contract terms.",
#         notif_type="contract_draft_update",
#         object_id=offer.job.contract.pk
#     )
#     
#     messages.success(request, "Offer accepted! A contract has been created. You can now negotiate the terms.")
#     return redirect("jobs:contract_draft_edit", pk=offer.job.contract.pk)


# DEPRECATED: Old offer system - use accept_application_new instead
# @login_required
# @require_POST
# def create_job_offer(request, application_pk):
#     """Create or update a job offer for an application"""
#     pass


@login_required
@require_POST
def reconsider_application(request, pk):
    """Reconsider a rejected application"""
    application = get_object_or_404(JobApplication, pk=pk)
    
    # Check if user is the job owner
    if request.user != application.job.owner:
        messages.error(request, "You are not authorized to reconsider this application.")
        return redirect("jobs:employer_dashboard")
    
    # Check if application is rejected
    if application.status.lower() != 'rejected':
        messages.warning(request, "This application is not rejected.")
        return redirect("jobs:employer_dashboard")
    
    # Change status back to pending
    application.status = 'Pending'
    application.save()
    
    # Send notification to worker
    Notification.objects.create(
        user=application.worker,
        message=f"Your application for '{application.job.title}' is being reconsidered by the employer.",
        notif_type="application_update",
        object_id=application.pk
    )
    
    messages.success(request, "Application has been moved back to pending for reconsideration.")
    return redirect("jobs:job_application_detail", pk=pk)


# DEPRECATED: Old offer system - use new workflow instead
# @login_required
# @require_POST
# def reject_job_offer(request, pk):
#     """Reject a job offer"""
#     pass


# ============================================
# NEW REDESIGNED WORKFLOW VIEWS
# ============================================

@login_required
@require_POST
def accept_application_new(request, pk):
    """Accept application and create contract for negotiation"""
    application = get_object_or_404(JobApplication, pk=pk)
    
    if request.user != application.job.owner:
        messages.error(request, "You are not authorized to accept this application.")
        return redirect("jobs:job_application_detail", pk=pk)
    
    # Update application status
    application.status = "Negotiation"
    application.save()
    
    # Create a dedicated contract for this application
    contract = Contract.objects.create(
        job=application.job,
        worker=application.worker,
        client=application.job.owner,
        application=application,
        status="Negotiation",
        job_title=application.job.title,
        job_description=application.job.description,
        agreed_rate=application.job.budget,
        rate_type="fixed",
        payment_schedule=application.job.payment_schedule or "End of Project",
        duration=application.job.duration or "To be determined",
        schedule=application.job.schedule or "To be determined",
        start_date=application.available_start_date or timezone.now().date(),
        terms=DEFAULT_CONTRACT_TERMS,
    )
    
    # Send notification to worker
    Notification.objects.create(
        user=application.worker,
        message=f"Your application for '{application.job.title}' has been accepted! Please review and negotiate the contract terms.",
        notif_type="contract_negotiation",
        object_id=contract.pk
    )
    
    messages.success(request, "Application accepted! Contract created for negotiation.")
    return redirect("jobs:contract_negotiation", pk=contract.pk)


class ContractNegotiationView(LoginRequiredMixin, UpdateView):
    """View for contract negotiation - both parties can edit"""
    model = Contract
    template_name = "jobs/contract_negotiation.html"
    fields = [
        'job_title',
        'job_description',
        'agreed_rate',
        'rate_type',
        'payment_schedule',
        'duration',
        'schedule',
        'start_date',
        'end_date',
        'start_time',
        'end_time',
        'notes',
        'terms',
    ]
    
    def dispatch(self, request, *args, **kwargs):
        contract = self.get_object()
        
        # Check if user is authorized (include application relations as fallback)
        authorized_user_ids = {contract.worker_id, contract.client_id}
        if contract.application:
            authorized_user_ids.add(contract.application.worker_id)
            authorized_user_ids.add(contract.application.job.owner_id)

        if request.user.id not in authorized_user_ids:
            messages.error(request, "You are not authorized to view this contract.")
            return redirect("jobs:job_list")
        
        # Check if still in negotiation
        if contract.status != "Negotiation":
            messages.warning(request, "This contract is no longer in negotiation phase.")
            return redirect("jobs:contract_detail", pk=contract.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.get_object()
        context['is_worker'] = self.request.user == contract.worker
        context['is_employer'] = self.request.user == contract.client
        context['default_contract_terms'] = DEFAULT_CONTRACT_TERMS
        terms_source = contract.terms or DEFAULT_CONTRACT_TERMS
        context['prefilled_terms'] = normalize_contract_terms_text(terms_source) or DEFAULT_CONTRACT_TERMS
        
        # Check worker availability conflicts
        if contract.start_date and contract.end_date and contract.start_time and contract.end_time:
            from .models import WorkerAvailability
            availability_result = WorkerAvailability.check_availability_for_contract(
                worker=contract.worker,
                start_date=contract.start_date,
                end_date=contract.end_date,
                start_time=contract.start_time,
                end_time=contract.end_time
            )
            context['has_availability_conflicts'] = not availability_result['available']
            context['availability_conflicts'] = availability_result['conflicts'][:10]  # Show first 10 conflicts
            context['total_conflicts'] = len(availability_result['conflicts'])
        else:
            context['has_availability_conflicts'] = False
            context['availability_conflicts'] = []
            context['total_conflicts'] = 0
        
        return context
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not form.is_bound:
            terms_source = form.instance.terms or DEFAULT_CONTRACT_TERMS
            normalized_terms = normalize_contract_terms_text(terms_source) or DEFAULT_CONTRACT_TERMS
            form.initial['terms'] = normalized_terms
            form.fields['terms'].initial = normalized_terms
        return form

    def form_valid(self, form):
        contract = form.save(commit=False)
        contract.status = "Negotiation"
        contract.is_finalized = False
        contract.finalized_by_worker = False
        contract.finalized_by_employer = False
        contract.worker_accepted = False
        contract.client_accepted = False
        contract.updated_at = timezone.now()
        contract.terms = normalize_contract_terms_text(contract.terms) or DEFAULT_CONTRACT_TERMS
        contract.save()
        form.save_m2m()

        action = self.request.POST.get("action", "submit")
        if action == "save_draft":
            messages.success(self.request, "Draft saved. Share with the other party when ready.")
        else:
            messages.success(self.request, "Contract terms updated successfully!")
            
            # Notify the other party about the update
            other_user = contract.client if self.request.user == contract.worker else contract.worker
            role = "Worker" if self.request.user == contract.worker else "Employer"
            Notification.objects.create(
                user=other_user,
                message=f"{role} has updated the contract terms for '{contract.job.title}'. Please review the changes.",
                notif_type="contract_updated",
                object_id=contract.pk
            )

        return redirect("jobs:contract_detail", pk=contract.pk)

    def get_success_url(self):
        return reverse("jobs:contract_detail", kwargs={"pk": self.object.pk})


@login_required
@require_POST
def accept_contract_terms(request, pk):
    """Accept contract terms during negotiation"""
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.user not in [contract.worker, contract.client]:
        messages.error(request, "You are not authorized to accept this contract.")
        return redirect("jobs:contract_detail", pk=pk)
    
    if contract.status != "Negotiation":
        messages.error(request, "Contract is not in negotiation phase.")
        return redirect("jobs:contract_detail", pk=pk)
    
    if request.POST.get("agree_terms") != "on":
        messages.error(request, "Please acknowledge the agreement before accepting the contract.")
        return redirect("jobs:contract_detail", pk=pk)

    # Check for schedule conflicts if worker is accepting
    if request.user == contract.worker and contract.start_date:
        from .schedule_utils import check_schedule_conflicts
        
        has_conflict, conflicting_contracts, warning_message = check_schedule_conflicts(
            worker_id=request.user.id,
            start_date=contract.start_date,
            end_date=contract.end_date,
            start_time=contract.start_time,
            end_time=contract.end_time,
            exclude_contract_id=contract.id
        )
        
        if has_conflict:
            # Store conflict warning in session to display on contract page
            request.session['schedule_conflict_warning'] = warning_message
            request.session['conflicting_contract_ids'] = [c.id for c in conflicting_contracts]
            
            # Check if user confirmed they want to proceed despite conflict
            if request.POST.get("confirm_despite_conflict") != "on":
                messages.warning(
                    request, 
                    mark_safe(
                        f"{warning_message.replace(chr(10), '<br>')}<br><br>"
                        f"<strong>Please confirm you can manage these commitments before accepting.</strong>"
                    )
                )
                return redirect("jobs:contract_negotiation", pk=pk)

    # Mark acceptance
    if request.user == contract.worker:
        contract.finalized_by_worker = True
        contract.worker_accepted = True
    else:
        contract.finalized_by_employer = True
        contract.client_accepted = True
    
    contract.save()
    
    # Check if both accepted
    if contract.finalized_by_worker and contract.finalized_by_employer:
        contract.status = "Finalized"
        contract.is_finalized = True
        contract.save()

        if contract.application:
            contract.application.status = "Archived"
            contract.application.save(update_fields=["status", "updated_at"])

        # Notify both parties
        Notification.objects.create(
            user=contract.worker,
            message=f"Contract for '{contract.job.title}' has been finalized! You can now start work.",
            notif_type="contract_finalized",
            object_id=contract.pk
        )
        Notification.objects.create(
            user=contract.client,
            message=f"Contract for '{contract.job.title}' has been finalized!",
            notif_type="contract_finalized",
            object_id=contract.pk
        )
        
        messages.success(request, "Contract finalized! Both parties have accepted.")
    else:
        # Notify the other party
        other_user = contract.client if request.user == contract.worker else contract.worker
        role = "Worker" if request.user == contract.worker else "Employer"
        Notification.objects.create(
            user=other_user,
            message=f"{role} has accepted the contract for '{contract.job.title}'. Please review and accept.",
            notif_type="contract_acceptance",
            object_id=contract.pk
        )
        
        messages.success(request, "You have accepted the contract. Waiting for the other party to accept.")
    
    return redirect("jobs:contract_detail", pk=contract.pk)


class JobTrackingView(LoginRequiredMixin, DetailView):
    """View for tracking job progress"""
    model = Contract
    template_name = "jobs/job_tracking.html"
    context_object_name = "contract"
    
    def get_queryset(self):
        return Contract.objects.filter(
            Q(client=self.request.user) | Q(worker=self.request.user)
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.get_object()
        
        # Get progress updates
        from .models import JobProgress
        progress_updates = contract.progress_updates.all().order_by('-created_at')
        progress_logs = contract.progress_logs.all().order_by('-timestamp')

        context['progress_updates'] = progress_updates
        context['progress_logs'] = progress_logs
        context['has_activity'] = progress_updates.exists() or progress_logs.exists()
        context['is_worker'] = self.request.user == contract.worker
        context['is_employer'] = self.request.user == contract.client
        context['can_start'] = context['is_worker'] and contract.status in {"Finalized", "Accepted"}
        context['can_post_progress'] = context['is_worker'] and contract.status == "In Progress"
        context['can_mark_completed'] = context['is_worker'] and contract.status == "In Progress"
        context['show_revision_request'] = context['is_worker'] and contract.is_revision_requested
        context['show_employer_review_actions'] = context['is_employer'] and contract.status == "Awaiting Review"

        return context


@login_required
@require_POST
def post_progress_update(request, contract_pk):
    """Worker posts a progress update"""
    from .models import JobProgress
    
    contract = get_object_or_404(Contract, pk=contract_pk)
    
    if request.user != contract.worker:
        messages.error(request, "Only the worker can post progress updates.")
        return redirect("jobs:job_tracking", pk=contract_pk)
    
    update_text = request.POST.get('update_text')
    image = request.FILES.get('image')
    
    if not update_text:
        messages.error(request, "Please provide an update description.")
        return redirect("jobs:job_tracking", pk=contract_pk)
    
    # Create progress update
    JobProgress.objects.create(
        contract=contract,
        update_text=update_text,
        image=image,
        updated_by=request.user
    )
    
    # Notify employer
    Notification.objects.create(
        user=contract.client,
        message=f"{contract.worker.username} posted a progress update for '{contract.job.title}'.",
        notif_type="progress_update",
        object_id=contract.pk
    )
    
    messages.success(request, "Progress update posted successfully!")
    return redirect("jobs:job_tracking", pk=contract_pk)


@login_required
@require_POST
def mark_job_completed(request, pk):
    """Worker marks job as completed"""
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.user != contract.worker:
        messages.error(request, "Only the worker can mark the job as completed.")
        return redirect("jobs:job_tracking", pk=pk)
    
    if contract.status != "In Progress":
        messages.error(request, "Job must be in progress to mark as completed.")
        return redirect("jobs:job_tracking", pk=pk)
    
    contract.status = "Awaiting Review"
    contract.completed_at = timezone.now()
    contract.is_revision_requested = False
    contract.save()
    
    # Notify employer
    Notification.objects.create(
        user=contract.client,
        message=f"{contract.worker.username} has marked '{contract.job.title}' as completed. Please review.",
        notif_type="contract_completed",
        object_id=contract.pk
    )
    
    messages.success(request, "Job marked as completed! Waiting for employer review.")
    return redirect("jobs:job_tracking", pk=pk)


@login_required
@require_POST
def end_job(request, pk):
    """Employer ends the job after review"""
    contract = get_object_or_404(Contract, pk=pk)
    
    if request.user != contract.client:
        messages.error(request, "Only the employer can end the job.")
        return redirect("jobs:job_tracking", pk=pk)
    
    if contract.status != "Awaiting Review":
        messages.error(request, "Job must be awaiting review to end.")
        return redirect("jobs:job_tracking", pk=pk)
    
    contract.status = "Completed"
    contract.save()
    
    # Only deactivate job if all vacancies are filled (no more positions available)
    job = contract.job
    if job.is_active and job.vacancies == 0:
        job.is_active = False
        job.save()
        messages.info(request, "All positions for this job have been filled. The job posting has been automatically deactivated.")
    
    # Notify worker
    Notification.objects.create(
        user=contract.worker,
        message=f"The employer has marked '{contract.job.title}' as completed.",
        notif_type="job_completed",
        object_id=contract.pk
    )
    
    messages.success(request, "Job completed! The job posting has been automatically archived. You and the worker can now exchange feedback.")
    return redirect("jobs:feedback_form", contract_pk=pk)


@login_required
@require_POST
def oppose_job_completion(request, pk):
    """Employer requests revisions instead of marking job completed"""
    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.client:
        messages.error(request, "Only the employer can oppose completion.")
        return redirect("jobs:job_tracking", pk=pk)

    if contract.status != "Awaiting Review":
        messages.error(request, "Job must be awaiting review to oppose completion.")
        return redirect("jobs:job_tracking", pk=pk)

    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Please provide a reason for opposing completion.")
        return redirect("jobs:job_tracking", pk=pk)

    contract.status = "In Progress"
    contract.is_revision_requested = True
    contract.completed_at = None
    contract.save()

    ProgressLog.objects.create(
        contract=contract,
        status="Revision Requested",
        message=reason,
        updated_by=request.user
    )

    Notification.objects.create(
        user=contract.worker,
        message=f"{contract.client.get_full_name() or contract.client.username} requested revisions for '{contract.job.title}': {reason}",
        notif_type="revision_requested",
        object_id=contract.pk
    )

    messages.success(request, "Revision requested. The job has been moved back to In Progress.")
    return redirect("jobs:job_tracking", pk=pk)


@login_required
def feedback_form(request, contract_pk):
    """View for submitting feedback"""
    from .models import Feedback
    
    contract = get_object_or_404(Contract, pk=contract_pk)
    
    if request.user not in [contract.worker, contract.client]:
        messages.error(request, "You are not authorized to give feedback for this contract.")
        return redirect("jobs:job_list")

    if contract.status != "Completed":
        messages.error(request, "Feedback can only be given for completed contracts.")
        return redirect("jobs:contract_detail", pk=contract_pk)

    if Feedback.objects.filter(contract=contract, giver=request.user).exists():
        messages.info(request, "You have already provided feedback for this contract.")
        return redirect("jobs:contract_detail", pk=contract_pk)

    receiver = contract.client if request.user == contract.worker else contract.worker

    if request.method == "POST":
        rating = request.POST.get('rating')
        message = request.POST.get('message')
        
        if not rating or not message:
            messages.error(request, "Please provide both rating and feedback message.")
            return redirect("jobs:feedback_form", contract_pk=contract_pk)
        
        # Create feedback
        Feedback.objects.create(
            contract=contract,
            giver=request.user,
            receiver=receiver,
            rating=int(rating),
            message=message
        )
        
        # Notify receiver
        Notification.objects.create(
            user=receiver,
            message=f"{request.user.username} left you feedback for '{contract.job.title}'.",
            notif_type="feedback",
            object_id=contract.pk
        )
        
        messages.success(request, "Feedback submitted successfully!")
        return redirect("jobs:contract_detail", pk=contract_pk)
    
    context = {
        'contract': contract,
        'receiver': receiver,
        'is_worker': request.user == contract.worker
    }

    return render(request, "jobs/feedback_form.html", context)


class ContractFeedbackDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = "jobs/feedback_detail.html"
    context_object_name = "contract"

    def dispatch(self, request, *args, **kwargs):
        contract = self.get_object()
        if request.user not in [contract.client, contract.worker]:
            messages.error(request, "You are not authorized to view this feedback.")
            return redirect("jobs:job_list")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contract = self.object
        feedbacks = contract.feedbacks.select_related("giver", "receiver").order_by("-created_at")
        worker_feedback = feedbacks.filter(receiver=contract.worker).first()
        employer_feedback = feedbacks.filter(receiver=contract.client).first()

        user_feedback = feedbacks.filter(giver=self.request.user).first()

        context["feedbacks"] = feedbacks
        context["worker_feedback"] = worker_feedback
        context["employer_feedback"] = employer_feedback
        context["user_feedback"] = user_feedback
        context["is_employer"] = self.request.user == contract.client
        context["is_worker"] = self.request.user == contract.worker
        context["can_leave_feedback"] = (
            contract.status == "Completed"
            and user_feedback is None
            and self.request.user in [contract.client, contract.worker]
        )
        return context


@login_required
def employer_applications_view(request):
    """View for employer to see all applications"""
    # Get all applications for employer's jobs
    applications = JobApplication.objects.filter(
        job__owner=request.user
    ).select_related('worker', 'job').order_by('-applied_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by job if provided
    job_filter = request.GET.get('job')
    if job_filter:
        applications = applications.filter(job_id=job_filter)
    
    # Get user's jobs for filter dropdown
    user_jobs = Job.objects.filter(owner=request.user)
    
    context = {
        'applications': applications,
        'user_jobs': user_jobs,
    }
    
    return render(request, "jobs/employer_applications.html", context)


@login_required
def employer_contracts_view(request):
    """View for employer to see all contracts"""
    contracts = Contract.objects.filter(
        client=request.user
    ).select_related('worker', 'job').order_by('-updated_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        contracts = contracts.filter(status=status_filter)
    
    context = {
        'contracts': contracts,
    }
    
    return render(request, "jobs/employer_contracts.html", context)


@login_required
def worker_applications_view(request):
    """View for worker to see their applications"""
    applications = JobApplication.objects.filter(
        worker=request.user
    ).select_related('job', 'job__owner').order_by('-applied_at')
    
    context = {
        'applications': applications,
    }
    
    return render(request, "jobs/worker_applications.html", context)


@login_required
def worker_contracts_view(request):
    """View for worker to see their contracts"""
    contracts = Contract.objects.filter(
        worker=request.user
    ).select_related('client', 'job').order_by('-updated_at')
    
    context = {
        'contracts': contracts,
    }
    
    return render(request, "jobs/worker_contracts.html", context)


@login_required
@require_POST
def start_contract_work(request, pk):
    """Start contract work"""
    contract = get_object_or_404(Contract, pk=pk)

    if request.user != contract.worker:
        messages.error(request, "You are not authorized to start this contract.")
        return redirect("jobs:contract_detail", pk=pk)

    if contract.status == "In Progress":
        messages.info(request, "Work on this contract has already started.")
        return redirect("jobs:job_tracking", pk=pk)

    if contract.status not in ["Finalized", "Accepted"]:
        messages.warning(request, "This contract must be finalized before work can start.")
        return redirect("jobs:contract_detail", pk=pk)

    contract.start_work()

    Notification.objects.create(
        user=contract.client,
        message=f"{contract.worker.get_full_name() or contract.worker.username} has started working on '{contract.job.title}'.",
        notif_type="contract_start",
        object_id=contract.pk
    )

    messages.success(request, "Great! The contract is now marked as In Progress.")
    return redirect("jobs:job_tracking", pk=pk)


# ============================================================================
# Calendar and Schedule API Views
# ============================================================================

@login_required
def get_schedule_events(request):
    """
    API endpoint to get calendar events for worker's schedule.
    Returns contract data formatted for FullCalendar.
    """
    from .schedule_utils import get_worker_schedule
    from datetime import datetime, timedelta
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Get date range from query params
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        
        if start_str and end_str:
            # Handle timezone format - replace +08:00 format and remove timezone info
            start_str_clean = start_str.split('T')[0]  # Just get the date part
            end_str_clean = end_str.split('T')[0]  # Just get the date part
            start_date = datetime.strptime(start_str_clean, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str_clean, '%Y-%m-%d').date()
        else:
            # Default to current month
            today = datetime.now().date()
            start_date = today.replace(day=1)
            # Get last day of month
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        logger.info(f"Fetching schedule for user {request.user.id} from {start_date} to {end_date}")
        events = get_worker_schedule(request.user.id, start_date, end_date)
        logger.info(f"Returning {len(events)} events")
        
        return JsonResponse(events, safe=False)
    except Exception as e:
        logger.error(f"Error in get_schedule_events: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def check_contract_conflict(request):
    """
    API endpoint to check for schedule conflicts before accepting a contract.
    """
    from .schedule_utils import check_schedule_conflicts
    import json
    
    try:
        data = json.loads(request.body)
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        contract_id = data.get('contract_id')
        
        if not start_date_str:
            return JsonResponse({'error': 'Start date is required'}, status=400)
        
        start_date = datetime.fromisoformat(start_date_str).date()
        end_date = datetime.fromisoformat(end_date_str).date() if end_date_str else None
        
        # Get start_time and end_time if provided
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        start_time = datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None
        end_time = datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None
        
        has_conflict, conflicting_contracts, warning_message = check_schedule_conflicts(
            worker_id=request.user.id,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            exclude_contract_id=contract_id
        )
        
        conflicts_data = []
        for contract in conflicting_contracts:
            conflicts_data.append({
                'id': contract.id,
                'title': contract.job.title,
                'start_date': contract.start_date.isoformat(),
                'end_date': contract.end_date.isoformat() if contract.end_date else None,
                'client': contract.client.get_full_name() or contract.client.username,
                'status': contract.status,
            })
        
        return JsonResponse({
            'has_conflict': has_conflict,
            'conflicts': conflicts_data,
            'warning_message': warning_message,
            'conflict_count': len(conflicting_contracts)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def get_upcoming_deadlines_api(request):
    """
    API endpoint to get upcoming contract deadlines.
    """
    from .schedule_utils import get_upcoming_deadlines
    
    days_ahead = int(request.GET.get('days', 7))
    deadlines = get_upcoming_deadlines(request.user.id, days_ahead)
    
    # Convert dates to ISO format
    for deadline in deadlines:
        deadline['deadline'] = deadline['deadline'].isoformat()
    
    return JsonResponse({'deadlines': deadlines})


@login_required
@require_POST
def toggle_job_status(request, job_id):
    """
    Toggle job post active/inactive status.
    Only the job owner can toggle the status.
    """
    print(f"=== TOGGLE JOB STATUS CALLED ===")
    print(f"Job ID: {job_id}")
    print(f"User: {request.user}")
    print(f"Method: {request.method}")
    print(f"Headers: {dict(request.headers)}")
    
    job = get_object_or_404(Job, id=job_id)
    print(f"Job found: {job.title}, Owner: {job.owner}")
    
    # Check if user is the owner
    if job.owner != request.user:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to modify this job.'
        }, status=403)
    
    try:
        # Toggle the status
        job.is_active = not job.is_active
        job.save()
        
        # Log activity (wrapped in try-except in case ActivityLog table doesn't exist yet)
        try:
            from users.activity_logger import log_activity
            if job.is_active:
                log_activity(
                    user=request.user,
                    activity_type='job_updated',
                    description=f"Activated job post: {job.title}",
                    related_object=job,
                    metadata={'job_id': job.id, 'action': 'activated'}
                )
            else:
                log_activity(
                    user=request.user,
                    activity_type='job_updated',
                    description=f"Deactivated job post: {job.title}",
                    related_object=job,
                    metadata={'job_id': job.id, 'action': 'deactivated'}
                )
        except Exception as e:
            # Activity logging failed, but continue (don't break the toggle functionality)
            print(f"Activity logging failed: {e}")
        
        # Set success message
        if job.is_active:
            message = f'Job "{job.title}" has been activated and is now visible to workers.'
        else:
            message = f'Job "{job.title}" has been deactivated and is no longer visible to workers.'
        
        messages.success(request, message)
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            return JsonResponse({
                'success': True,
                'is_active': job.is_active,
                'message': message
            })
        else:
            # Redirect to job list or referrer
            return redirect(request.META.get('HTTP_REFERER', 'jobs:job_list'))
    
    except Exception as e:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
        else:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect(request.META.get('HTTP_REFERER', 'jobs:job_list'))


class FAQView(TemplateView):
    """View for the FAQ page"""
    template_name = "mainpages/faq.html"


class TermsOfServiceView(TemplateView):
    """View for the Terms of Service page"""
    template_name = "mainpages/terms_of_service.html"


class PrivacyPolicyView(TemplateView):
    """View for the Privacy Policy page"""
    template_name = "mainpages/privacy_policy.html"


@login_required
def worker_calendar_api(request):
    """
    API endpoint to return worker's contracts in FullCalendar format.
    Each contract generates multiple daily events showing actual work hours.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    worker = request.user
    
    # Get date range from query params (optional)
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    # Convert to date objects if provided
    if start_date:
        start_date = datetime.fromisoformat(start_date.replace('Z', '')).date()
    if end_date:
        end_date = datetime.fromisoformat(end_date.replace('Z', '')).date()
    
    # Get worker's contracts
    contracts = Contract.get_worker_schedule(worker, start_date, end_date)
    
    logger.info(f"Calendar API: Found {contracts.count()} contracts for {worker.username}")
    
    # Convert to calendar events (each contract returns a list of daily events)
    events = []
    for contract in contracts:
        logger.info(f"Processing contract {contract.id}: {contract.job_title}, Status: {contract.status}, Dates: {contract.start_date} to {contract.end_date}, Times: {contract.start_time} - {contract.end_time}")
        
        event_data = contract.get_calendar_event_data()
        if event_data:
            # event_data is now a list of events (one per day)
            if isinstance(event_data, list):
                logger.info(f"Contract {contract.id} generated {len(event_data)} daily events")
                events.extend(event_data)
            else:
                # Backward compatibility if old format
                logger.info(f"Contract {contract.id} generated 1 event (old format)")
                events.append(event_data)
        else:
            logger.warning(f"Contract {contract.id} returned no events (missing dates?)")
    
    logger.info(f"Calendar API: Returning {len(events)} total events")
    
    return JsonResponse(events, safe=False)


@login_required
def check_contract_conflict(request):
    """
    API endpoint to check if a contract has time conflicts
    Expects POST with: start_date, end_date, start_time, end_time
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        contract_id = data.get('contract_id')  # Optional, for editing existing contract
        
        # Create a temporary contract to check conflicts
        temp_contract = Contract(
            worker=request.user,
            start_date=start_date,
            end_date=end_date,
            start_time=start_time,
            end_time=end_time,
            pk=contract_id  # If editing, use existing ID
        )
        
        conflicts = temp_contract.check_time_conflict()
        
        if conflicts:
            return JsonResponse({
                'has_conflict': True,
                'conflicts': conflicts
            })
        else:
            return JsonResponse({
                'has_conflict': False,
                'message': 'No time conflicts found'
            })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
