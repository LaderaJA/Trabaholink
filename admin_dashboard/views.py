from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, DeleteView, TemplateView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from users.models import CustomUser
from messaging.models import Conversation
from reports.models import Report
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from .models import ModeratedWord
from .forms import ModeratedWordForm
from django.contrib.auth import get_user_model
from announcements.models import Announcement


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
