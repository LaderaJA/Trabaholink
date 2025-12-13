from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.urls import reverse_lazy
from .models import Announcement

class AnnouncementListView(ListView):
    model = Announcement
    template_name = "announcements/announcement_list.html"
    context_object_name = "announcements"

    def get_queryset(self):
        try:
            return Announcement.objects.filter(is_active=True).order_by("-created_at")
        except Exception:
            # In case older DBs don't have is_active yet
            return Announcement.objects.all().order_by("-created_at")

class AnnouncementDetailView(DetailView):
    model = Announcement
    template_name = "announcements/announcement_detail.html"
    context_object_name = "announcement"

    def get_queryset(self):
        try:
            return Announcement.objects.filter(is_active=True)
        except Exception:
            return Announcement.objects.all()

class AnnouncementCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Announcement
    template_name = "announcements/announcement_form.html"
    fields = ["title", "description", "image"]
    success_url = reverse_lazy("announcements:announcement_list")

    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        return super().form_valid(form)

    def test_func(self):
        return self.request.user.is_staff  
