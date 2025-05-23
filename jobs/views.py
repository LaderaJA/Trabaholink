import json
from django.http import HttpResponseRedirect, JsonResponse
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse, reverse_lazy
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.db.models import Q
from .utils import get_users_who_applied
from .models import Job, JobCategory, JobImage, JobApplication, Contract
from .forms import JobForm, JobApplicationForm, JobImageForm
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator


# Homepage View (Static Landing Page)
class HomePageView(TemplateView):
    template_name = "mainpages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = JobCategory.objects.all()
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
        queryset = Job.objects.all().select_related("category")
        request = self.request

        # Filters
        category_id = request.GET.get("category")
        keyword = request.GET.get("q")
        user_lat = request.GET.get("lat")
        user_lng = request.GET.get("lng")
        min_budget = request.GET.get("min_budget")
        max_budget = request.GET.get("max_budget")
        municipality = request.GET.get("municipality")
        barangay = request.GET.get("barangay")
        sort = request.GET.get("sort", "date_desc")  # Default: newest first

        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if keyword:
            queryset = queryset.filter(
                Q(title__icontains=keyword) | Q(description__icontains=keyword)
            )
        if min_budget:
            queryset = queryset.filter(budget__gte=min_budget)
        if max_budget:
            queryset = queryset.filter(budget__lte=max_budget)
        if municipality:
            queryset = queryset.filter(municipality__icontains=municipality)
        if barangay:
            queryset = queryset.filter(barangay__icontains=barangay)

        self.user_location = None
        if user_lat and user_lng:
            try:
                self.user_location = Point(float(user_lng), float(user_lat), srid=4326)
                queryset = queryset.annotate(distance=Distance("location", self.user_location))
            except (ValueError, TypeError):
                self.user_location = None

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
        context["user_location"] = self.user_location

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
                    applicants = applicants.filter(worker__username__icontains=search_query)

                # Paginate the applicants
                paginator = Paginator(applicants, 5)  # Show 5 applicants per page
                page_number = self.request.GET.get("page")
                page_obj = paginator.get_page(page_number)

                context["applicants"] = page_obj
                context["search_query"] = search_query

            # Check if the user has already applied for the job
            context["has_applied"] = job.applications.filter(worker=user).exists()

        return context

# 🔹 Job Create View (with geolocation support)
class JobCreateView(LoginRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("jobs:job_list")

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

        # Create Job object
        job = form.save(commit=False)
        job.owner = self.request.user

        # Handle location
        lat = self.request.POST.get("latitude")
        lng = self.request.POST.get("longitude")
        if lat and lng:
            job.location = Point(float(lng), float(lat), srid=4326)

        job.save()

        # Handle images
        files = self.request.FILES.getlist('images')
        if files:
            for f in files:
                JobImage.objects.create(job=job, image=f)

        # Redirect to success URL
        return redirect(self.success_url)
# 🔹 Job Update View (Only job owners can edit)
class JobUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    
    def test_func(self):
        return self.request.user == self.get_object().owner
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['image_form'] = JobImageForm(self.request.POST, self.request.FILES)
        else:
            context['image_form'] = JobImageForm()
        context['existing_images'] = self.object.jobimage_set.all()
        return context
    
    def form_valid(self, form):
        # Handle location
        lat = self.request.POST.get("latitude")
        lng = self.request.POST.get("longitude")
        if lat and lng:
            form.instance.location = Point(float(lng), float(lat), srid=4326)
        
        response = super().form_valid(form)
        
        files = self.request.FILES.getlist('images')
        if files:
            for img in files:
                JobImage.objects.create(job=self.object, image=img)
        
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

    def form_valid(self, form):
        form.instance.worker = self.request.user
        form.instance.job = get_object_or_404(Job, pk=self.kwargs["pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("jobs:job_detail", kwargs={"pk": self.object.job.pk})

# 🔹 Contract Detail View
class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = "jobs/contract_detail.html"
    context_object_name = "contract"

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
