from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from jobs.models import Job
from services.models import ServicePost

class CombinedPostListView(LoginRequiredMixin, ListView):
    template_name = "posts/combined_post_list.html"
    context_object_name = "posts"
    paginate_by = 12

    def get_queryset(self):
        filter_type = self.request.GET.get("type", "all")
        items = []
        if filter_type == "job":
            items.extend(Job.objects.filter(is_active=True))
        elif filter_type == "service":
            items.extend(ServicePost.objects.filter(is_active=True))
        else:
            items.extend(Job.objects.filter(is_active=True))
            items.extend(ServicePost.objects.filter(is_active=True))
        # Sort by created_at descending (newest first)
        return sorted(items, key=lambda p: p.created_at, reverse=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_type"] = self.request.GET.get("type", "all")
        return context
