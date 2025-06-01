from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, DeleteView, TemplateView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from users.models import CustomUser, Skill
from messaging.models import Conversation
from reports.models import Report
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from .models import ModeratedWord
from .forms import ModeratedWordForm
from announcements.forms import AnnouncementForm
from django.contrib.auth import get_user_model
from announcements.models import Announcement
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from jobs.models import Job
from .models import Report
import json
from django.views.decorators.http import require_POST


class DashboardMainView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard_main.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['total_reports'] = Report.objects.count()
        context['moderated_words_count'] = ModeratedWord.objects.count()
        context['total_announcements'] = Announcement.objects.count()

        return context
    
# Admin permission mixin
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# User Management Views
class UserListView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'admin_dashboard/user_list.html'
    context_object_name = 'users'

class UserDetailView(AdminRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'admin_dashboard/user_detail.html'
    context_object_name = 'selected_user'  # Use a custom context variable name

    def get_object(self, queryset=None):
        # Retrieve the user based on the primary key (pk) from the URL
        return get_object_or_404(CustomUser, pk=self.kwargs['pk'])

class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'admin_dashboard/user_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:user_list')

# Report Management Views
class ReportListView(AdminRequiredMixin, ListView):
    model = Report
    template_name = 'admin_dashboard/report_list.html'
    context_object_name = 'reports'

class ReportDetailView(AdminRequiredMixin, DetailView):
    model = Report
    template_name = 'admin_dashboard/report_detail.html'

def resolve_report(request, pk):
    report = get_object_or_404(Report, pk=pk)
    report.is_resolved = True
    report.save()
    messages.success(request, "Report marked as resolved.")
    return redirect('admin_dashboard:report_list')

# Flagged Chats Management Views
class FlaggedChatListView(AdminRequiredMixin, ListView):
    model = Conversation
    template_name = 'admin_dashboard/flagged_chat_list.html'
    context_object_name = 'flagged_chats'

    def get_queryset(self):
        return Conversation.objects.filter(is_flagged=True)

class FlaggedChatDetailView(AdminRequiredMixin, DetailView):
    model = Conversation
    template_name = 'admin_dashboard/flagged_chat_detail.html'



class ModeratedWordListView(ListView):
    model = ModeratedWord
    template_name = 'admin_dashboard/moderated_word_list.html'
    context_object_name = 'words'

class ModeratedWordCreateView(SuccessMessageMixin, CreateView):
    model = ModeratedWord
    form_class = ModeratedWordForm
    template_name = 'admin_dashboard/moderated_word_form.html'
    success_url = reverse_lazy('admin_dashboard:moderated_word_list')
    success_message = "Word added successfully."

class ModeratedWordUpdateView(SuccessMessageMixin, UpdateView):
    model = ModeratedWord
    form_class = ModeratedWordForm
    template_name = 'admin_dashboard/moderated_word_form.html'
    success_url = reverse_lazy('admin_dashboard:moderated_word_list')
    success_message = "Word updated successfully."

class ModeratedWordDeleteView(SuccessMessageMixin, DeleteView):
    model = ModeratedWord
    template_name = 'admin_dashboard/moderated_word_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:moderated_word_list')
    success_message = "Word deleted successfully."



# Announcement management

class AnnouncementCreateView(AdminRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'admin_dashboard/announcement_form.html'
    success_url = reverse_lazy('admin_dashboard:admin_announcement_list')
    success_message = "Announcement created successfully."

    
class AnnouncementSummaryView(AdminRequiredMixin, ListView):
    model = Announcement
    template_name = 'admin_dashboard/announcement_summary.html'
    context_object_name = 'announcements'
    ordering = ['-created_at']

class AnnouncementUpdateView(AdminRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'admin_dashboard/announcement_edit.html'
    success_url = reverse_lazy('admin_dashboard:admin_announcement_list')


class AnnouncementDeleteView(AdminRequiredMixin, DeleteView):
    model = Announcement
    template_name = 'admin_dashboard/announcement_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:admin_announcement_list')


@csrf_exempt
@login_required
def submit_report(request):
    if request.method == "POST":
        try:
            data = request.POST
            screenshot = request.FILES.get('screenshot')
            report_type = data.get("report_type")
            username = data.get("username")  # Updated to handle username
            content = data.get("content", "").strip()

            # Debugging: Log the received data
            print("Report Data:", data)
            print("Screenshot:", screenshot)

            if not content:
                return JsonResponse({"success": False, "message": "Report content cannot be empty."})

            # Create the report
            report = Report.objects.create(
                user=request.user,
                reported_content=content,
                report_type=report_type,
                screenshot=screenshot
            )

            # Handle specific entity types
            if report_type == "user" and username:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    reported_user = User.objects.get(username=username)
                    report.reported_user = reported_user
                    report.save()
                except User.DoesNotExist:
                    return JsonResponse({"success": False, "message": "User not found."})

            return JsonResponse({"success": True, "message": "Report submitted successfully."})
        except Exception as e:
            # Debugging: Log any errors
            print("Error saving report:", e)
            return JsonResponse({"success": False, "message": "An error occurred while saving the report."})

    return JsonResponse({"success": False, "message": "Invalid request method."})

@csrf_exempt
@login_required
@require_POST
def update_report_status(request):
    try:
        data = json.loads(request.body)
        report_id = data.get("report_id")
        new_status = data.get("status")
        
        # Basic validation
        if new_status not in ["pending", "reviewed", "resolved"]:
            return JsonResponse({"success": False, "message": "Invalid status value."})
        
        report = Report.objects.get(pk=report_id)
        report.status = new_status
        report.save()
        return JsonResponse({"success": True, "message": "Status updated successfully."})
    except Report.DoesNotExist:
        return JsonResponse({"success": False, "message": "Report not found."})
    except Exception as e:
        print("Error in update_report_status:", e)
        return JsonResponse({"success": False, "message": "An error occurred while updating the status."})

class PendingSkillListView(LoginRequiredMixin, ListView):
    model = Skill
    template_name = "admin_dashboard/pending_skill_list.html"
    context_object_name = "skills"

    def get_queryset(self):
        user_pk = self.kwargs.get("pk")
        return Skill.objects.filter(user__pk=user_pk, status="pending")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_obj"] = get_object_or_404(CustomUser, pk=self.kwargs.get("pk"))
        return context

class PendingSkillUpdateForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

class PendingSkillUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Skill
    form_class = PendingSkillUpdateForm
    template_name = "admin_dashboard/pending_skill_update.html"

    def test_func(self):
        # Optionally restrict update permission (for example, only staff users may update)
        return self.request.user.is_staff  # or customize your test

    def get_success_url(self):
        skill = self.get_object()
        return reverse_lazy('admin_dashboard:pending_skill_list', kwargs={'pk': skill.user.pk})
