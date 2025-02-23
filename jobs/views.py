from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from .models import Job, JobApplication, Contract, JobCategory
from .forms import JobForm, JobApplicationForm
from django.http import JsonResponse

# Homepage View (Static Landing Page)
class HomePageView(TemplateView):
    template_name = "mainpages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = JobCategory.objects.all()  
        return context



# 🔹 Job List View (Displays all jobs)
class JobListView(ListView):
    model = Job
    template_name = "jobs/job_list.html"
    context_object_name = "jobs"
    ordering = ["-created_at"]

# 🔹 Job Detail View (Displays job details)
class JobDetailView(DetailView):
    model = Job
    template_name = "jobs/job_detail.html"
    context_object_name = "job"

# 🔹 Job Create View (Only logged-in users can post)
class JobCreateView(LoginRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("job_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

# 🔹 Job Update View (Only job owners can edit)
class JobUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"

    def test_func(self):
        job = self.get_object()
        return self.request.user == job.owner

    def get_success_url(self):
        return reverse_lazy("job_detail", kwargs={"pk": self.object.pk})

# Job Delete View (Only job owners can delete)
class JobDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Job
    template_name = "jobs/job_confirm_delete.html"
    success_url = reverse_lazy("job_list")

    def test_func(self):
        job = self.get_object()
        return self.request.user == job.owner

# 🔹 Job Application View (Workers apply to jobs)
class JobApplicationCreateView(LoginRequiredMixin, CreateView):
    model = JobApplication
    form_class = JobApplicationForm
    template_name = "jobs/job_application_form.html"

    def form_valid(self, form):
        form.instance.worker = self.request.user
        form.instance.job = get_object_or_404(Job, pk=self.kwargs["pk"])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("job_detail", kwargs={"pk": self.object.job.pk})

# 🔹 Contract Detail View (Displays awarded contracts)
class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = "jobs/contract_detail.html"
    context_object_name = "contract"
