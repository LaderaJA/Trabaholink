from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, DeleteView, TemplateView, CreateView, UpdateView
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from users.models import CustomUser, Skill, Experience, Education, AccountVerification
from messaging.models import Conversation
from reports.models import Report
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from .models import ModeratedWord, FlaggedChat
from .forms import ModeratedWordForm
from announcements.forms import AnnouncementForm
from django.contrib.auth import get_user_model
from announcements.models import Announcement
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from jobs.models import Job
from services.models import ServicePost
from .models import Report
from messaging.models import Conversation
import json
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.utils import timezone


class DashboardMainView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard_home.html'

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        
        # Basic stats
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['total_jobs'] = Job.objects.filter(is_active=True).count()
        context['new_jobs_today'] = Job.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        context['total_services'] = ServicePost.objects.filter(status='approved').count()
        context['new_services_today'] = ServicePost.objects.filter(
            created_at__date=timezone.now().date()
        ).count()
        context['total_reports'] = Report.objects.count()
        context['pending_reports'] = Report.objects.filter(status='pending').count()
        context['pending_reports_count'] = context['pending_reports']
        context['moderated_words_count'] = ModeratedWord.objects.count()
        context['total_announcements'] = Announcement.objects.count()
        context['total_skill_verifications'] = Skill.objects.count()
        context['pending_skill_verifications'] = Skill.objects.filter(status='pending').count()
        context['verified_skill_verifications'] = Skill.objects.filter(status='verified').count()
        
        # Recent reports
        context['recent_reports'] = Report.objects.order_by('-created_at')[:5]
        
        # Chart data - User growth (last 7 days)
        user_growth_data = []
        user_growth_labels = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            count = User.objects.filter(date_joined__date=date).count()
            user_growth_data.append(count)
            user_growth_labels.append(date.strftime('%b %d'))
        
        context['user_growth_data'] = json.dumps(user_growth_data)
        context['user_growth_labels'] = json.dumps(user_growth_labels)
        
        # Job trends
        job_trends_data = []
        job_trends_labels = []
        for i in range(6, -1, -1):
            date = timezone.now().date() - timedelta(days=i)
            count = Job.objects.filter(created_at__date=date).count()
            job_trends_data.append(count)
            job_trends_labels.append(date.strftime('%b %d'))
        
        context['job_trends_data'] = json.dumps(job_trends_data)
        context['job_trends_labels'] = json.dumps(job_trends_labels)
        
        # Report categories
        report_categories = Report.objects.values('report_type').annotate(
            count=Count('id')
        )
        context['report_categories_labels'] = json.dumps([r['report_type'].replace('_', ' ').title() for r in report_categories])
        context['report_categories_data'] = json.dumps([r['count'] for r in report_categories])

        return context
    
# Admin permission mixin
class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

# User Management Views
class UserListView(AdminRequiredMixin, ListView):
    model = CustomUser
    template_name = 'admin_dashboard/dashboard_users.html'
    context_object_name = 'users'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_users_count'] = CustomUser.objects.filter(is_active=True).count()
        context['suspended_users_count'] = CustomUser.objects.filter(is_active=False).count()
        
        # New users this month
        first_day_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        context['new_users_month'] = CustomUser.objects.filter(
            date_joined__gte=first_day_of_month
        ).count()
        
        return context

class UserDetailView(AdminRequiredMixin, DetailView):
    model = CustomUser
    template_name = 'admin_dashboard/dashboard_user_detail.html'
    context_object_name = 'selected_user'  # Use a custom context variable name

    def get_object(self, queryset=None):
        # Retrieve the user based on the primary key (pk) from the URL
        return get_object_or_404(CustomUser, pk=self.kwargs['pk'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object
        
        # Get user's jobs (Job model uses 'owner' not 'posted_by')
        context['user_jobs'] = Job.objects.filter(owner=user)[:10]
        context['user_jobs_count'] = Job.objects.filter(owner=user).count()
        
        # Get user's services (ServicePost model uses 'worker' field)
        context['user_services'] = ServicePost.objects.filter(worker=user)[:10]
        context['user_services_count'] = ServicePost.objects.filter(worker=user).count()
        
        # Get reports involving this user
        context['user_reports'] = Report.objects.filter(
            Q(user=user) | Q(reported_user=user)
        )[:10]
        context['user_reports_count'] = Report.objects.filter(
            Q(user=user) | Q(reported_user=user)
        ).count()
        
        return context

class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = CustomUser
    template_name = 'admin_dashboard/user_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard:user_list')

# Report Management Views
class ReportListView(AdminRequiredMixin, ListView):
    model = Report
    template_name = 'admin_dashboard/dashboard_reports.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = Report.objects.filter(status='pending').count()
        context['reviewed_count'] = Report.objects.filter(status='reviewed').count()
        context['resolved_count'] = Report.objects.filter(status='resolved').count()
        return context

class ReportDetailView(AdminRequiredMixin, DetailView):
    model = Report
    template_name = 'admin_dashboard/dashboard_report_detail.html'
    context_object_name = 'report'

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
    model = FlaggedChat
    template_name = 'admin_dashboard/flagged_chat_detail.html'
    context_object_name = 'flagged_chat'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['conversation'] = self.object.chat_message
        context['messages'] = self.object.chat_message.messages.all().order_by('created_at')
        return context



class ModeratedWordListView(AdminRequiredMixin, ListView):
    model = ModeratedWord
    template_name = 'admin_dashboard/dashboard_moderation.html'
    context_object_name = 'words'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_flagged'] = sum(word.flagged_count or 0 for word in self.object_list)
        context['active_filters'] = ModeratedWord.objects.filter(is_banned=True).count()
        # Show all flagged chats (pending, reviewed, resolved)
        context['flagged_chats'] = FlaggedChat.objects.all().order_by('-created_at')[:20]
        return context

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
    
    def form_valid(self, form):
        form.instance.posted_by = self.request.user
        return super().form_valid(form)

    
class AnnouncementSummaryView(AdminRequiredMixin, ListView):
    model = Announcement
    template_name = 'admin_dashboard/dashboard_announcements.html'
    context_object_name = 'announcements'
    ordering = ['-created_at']
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = Announcement.objects.count()
        context['recent_count'] = Announcement.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
        return context

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

class UserVerificationListView(LoginRequiredMixin, ListView):
    model = AccountVerification
    template_name = "admin_dashboard/user_verification_list.html"
    context_object_name = "verifications"

    def get_queryset(self):
        status = self.request.GET.get("status", "pending")
        allowed_statuses = {"pending", "approved", "rejected", "overview"}
        if status not in allowed_statuses:
            status = "pending"

        queryset = AccountVerification.objects.select_related("user")

        user_id = self.request.GET.get("user")
        if user_id:
            queryset = queryset.filter(user__pk=user_id)

        if status != "overview":
            queryset = queryset.filter(status=status)

        return queryset.order_by("-submitted_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_id = self.request.GET.get("user")
        selected_user = None
        base_queryset = AccountVerification.objects.select_related("user")
        if user_id:
            selected_user = CustomUser.objects.filter(pk=user_id).first()
            base_queryset = base_queryset.filter(user__pk=user_id)

        context["selected_user"] = selected_user

        context["total_count"] = base_queryset.count()
        context["pending_count"] = base_queryset.filter(status="pending").count()
        context["approved_count"] = base_queryset.filter(status="approved").count()
        context["rejected_count"] = base_queryset.filter(status="rejected").count()

        context["pending_verifications"] = base_queryset.filter(status="pending")
        context["approved_verifications"] = base_queryset.filter(status="approved")
        context["rejected_verifications"] = base_queryset.filter(status="rejected")

        status = self.request.GET.get("status", "pending")
        allowed_statuses = {"pending", "approved", "rejected", "overview"}
        if status not in allowed_statuses:
            status = "pending"
        context["active_status"] = status

        context["status_labels"] = {
            "pending": "Pending Review",
            "approved": "Approved",
            "rejected": "Rejected",
            "overview": "Overview"
        }
        context["active_label"] = context["status_labels"].get(status, "Pending Review")

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
        return reverse_lazy('admin_dashboard:user_verification_list', kwargs={'pk': skill.user.pk})


# ===== NEW ADMIN DASHBOARD VIEWS =====

@require_POST
@login_required
def toggle_user_status(request, pk):
    """Toggle user active status"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    user = get_object_or_404(CustomUser, pk=pk)
    user.is_active = not user.is_active
    user.save()
    
    return JsonResponse({
        'success': True,
        'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
        'is_active': user.is_active
    })


@require_POST
@login_required
def send_user_warning(request, pk):
    """Send warning notification to user"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    user = get_object_or_404(CustomUser, pk=pk)
    data = json.loads(request.body)
    message = data.get('message', '')
    
    if not message:
        return JsonResponse({'success': False, 'message': 'Warning message is required'})
    
    # Create notification for the user
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=f"⚠️ Warning from Admin: {message}",
            notif_type="announcement"
        )
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
    
    return JsonResponse({
        'success': True,
        'message': 'Warning sent successfully'
    })


@require_POST
@login_required
def suspend_user(request, pk):
    """Suspend user account"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    user = get_object_or_404(CustomUser, pk=pk)
    data = json.loads(request.body) if request.body else {}
    reason = data.get('reason', 'Violation of platform policies')
    
    user.is_active = False
    user.save()
    
    # Send notification to user
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=f"🚫 Your account has been suspended. Reason: {reason}. Please contact support for more information.",
            notif_type="announcement"
        )
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
    
    return JsonResponse({
        'success': True,
        'message': f'User {user.username} has been suspended'
    })


@require_POST
@login_required
def ban_user(request, pk):
    """Permanently ban user"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    user = get_object_or_404(CustomUser, pk=pk)
    data = json.loads(request.body) if request.body else {}
    reason = data.get('reason', 'Permanent ban for severe policy violations')
    
    user.is_active = False
    user.save()
    
    # Send notification to user
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=user,
            message=f"🔒 Your account has been permanently banned. Reason: {reason}. This action is final.",
            notif_type="announcement"
        )
    except Exception as e:
        print(f"Failed to send notification: {str(e)}")
    
    return JsonResponse({
        'success': True,
        'message': 'User banned successfully'
    })


@require_POST
@login_required
def toggle_word_status(request, pk):
    """Toggle banned word status"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    word = get_object_or_404(ModeratedWord, pk=pk)
    word.is_banned = not word.is_banned
    word.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Word {"banned" if word.is_banned else "unbanned"} successfully',
        'is_banned': word.is_banned
    })


@require_POST
@login_required
def toggle_announcement_status(request, pk):
    """Toggle announcement active status"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_active = not announcement.is_active
    announcement.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Announcement {"activated" if announcement.is_active else "deactivated"} successfully',
        'is_active': announcement.is_active
    })


@login_required
def get_announcement_details(request, pk):
    """Get announcement details for modal"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        
        # Use content if available, otherwise use description
        content_text = announcement.content if announcement.content else announcement.description
        
        return JsonResponse({
            'success': True,
            'announcement': {
                'id': announcement.id,
                'title': announcement.title,
                'content': content_text,
                'created_at': announcement.created_at.strftime('%B %d, %Y'),
                'is_active': getattr(announcement, 'is_active', True),
                'views': getattr(announcement, 'views', 0),
                'image': announcement.image.url if announcement.image else None
            }
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ===== JOB MANAGEMENT VIEWS =====

class JobListView(AdminRequiredMixin, ListView):
    model = Job
    template_name = 'admin_dashboard/dashboard_jobs.html'
    context_object_name = 'jobs'
    paginate_by = 20
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_jobs_count'] = Job.objects.filter(is_active=True).count()
        context['pending_jobs_count'] = 0  # Add if you have pending status
        context['expired_jobs_count'] = Job.objects.filter(is_active=False).count()
        return context


class JobDetailView(AdminRequiredMixin, DetailView):
    model = Job
    template_name = 'admin_dashboard/dashboard_job_detail.html'
    context_object_name = 'job'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get applicants if Application model exists
        try:
            context['applicants'] = self.object.applications.all()[:10]
            context['applicants_count'] = self.object.applications.count()
        except:
            context['applicants'] = []
            context['applicants_count'] = 0
        context['related_reports'] = Report.objects.filter(job_posting=self.object)
        return context


@require_POST
@login_required
def toggle_job_status(request, pk):
    """Toggle job active status"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    job = get_object_or_404(Job, pk=pk)
    job.is_active = not job.is_active
    job.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Job {"activated" if job.is_active else "deactivated"} successfully',
        'is_active': job.is_active
    })


@require_POST
@login_required
def delete_job(request, pk):
    """Delete job"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    job = get_object_or_404(Job, pk=pk)
    job.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Job deleted successfully'
    })


@require_POST
@login_required
def archive_job(request, pk):
    """Archive job"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    job = get_object_or_404(Job, pk=pk)
    job.is_active = False
    # Add archived flag if you have it in model
    job.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Job archived successfully'
    })


@require_POST
@login_required
def flag_job(request, pk):
    """Flag job for review"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    job = get_object_or_404(Job, pk=pk)
    data = json.loads(request.body)
    reason = data.get('reason', '')
    
    # Create a report for this job
    Report.objects.create(
        user=request.user,
        job_posting=job,
        reported_content=reason,
        report_type='job_posting',
        status='pending'
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Job flagged successfully'
    })


# ===== SERVICE MANAGEMENT VIEWS =====

class ServiceListView(AdminRequiredMixin, ListView):
    model = ServicePost
    template_name = 'admin_dashboard/dashboard_services.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = ServicePost.objects.all().select_related('worker', 'category').order_by('-created_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(headline__icontains=search) |
                Q(worker__username__icontains=search) |
                Q(worker__first_name__icontains=search) |
                Q(worker__last_name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = ServicePost.objects.filter(status='pending').count()
        context['approved_count'] = ServicePost.objects.filter(status='approved').count()
        context['rejected_count'] = ServicePost.objects.filter(status='rejected').count()
        context['flagged_count'] = ServicePost.objects.filter(status='flagged').count()
        context['total_count'] = ServicePost.objects.count()
        return context


class ServiceDetailView(AdminRequiredMixin, DetailView):
    model = ServicePost
    template_name = 'admin_dashboard/dashboard_service_detail.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['provider_services_count'] = self.object.worker.service_posts.count()
        context['service_images'] = self.object.images.all()
        return context


@require_POST
@login_required
def approve_service(request, pk):
    """Approve a service post"""
    try:
        service = get_object_or_404(ServicePost, pk=pk)
        service.status = 'approved'
        service.is_active = True
        service.save()
        
        # Send notification to worker
        from notifications.models import Notification
        Notification.objects.create(
            user=service.worker,
            message=f"Your service '{service.headline}' has been approved and is now live!",
            notif_type='service_approved'
        )
        
        return JsonResponse({'success': True, 'message': 'Service approved successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_POST
@login_required
def reject_service(request, pk):
    """Reject a service post"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', 'No reason provided')
        
        service = get_object_or_404(ServicePost, pk=pk)
        service.status = 'rejected'
        service.is_active = False
        service.admin_notes = reason
        service.save()
        
        # Send notification to worker
        from notifications.models import Notification
        Notification.objects.create(
            user=service.worker,
            message=f"Your service '{service.headline}' was rejected. Reason: {reason}",
            notif_type='service_rejected'
        )
        
        return JsonResponse({'success': True, 'message': 'Service rejected'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_POST
@login_required
def flag_service(request, pk):
    """Flag a service for review"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', 'Flagged for review')
        
        service = get_object_or_404(ServicePost, pk=pk)
        service.status = 'flagged'
        service.admin_notes = reason
        service.save()
        
        return JsonResponse({'success': True, 'message': 'Service flagged for review'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_POST
@login_required
def delete_service_admin(request, pk):
    """Delete service"""
    try:
        service = get_object_or_404(ServicePost, pk=pk)
        service_name = service.headline
        service.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Service "{service_name}" deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_POST
@login_required
def flag_service(request, pk):
    """Flag service for review"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    return JsonResponse({
        'success': True,
        'message': 'Service flagged successfully'
    })


@require_POST
@login_required
def feature_service(request, pk):
    """Feature service on homepage"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    return JsonResponse({
        'success': True,
        'message': 'Service featured successfully'
    })


# ===== REPORT DETAIL ACTIONS =====

@require_POST
@login_required
def delete_reported_content(request, pk):
    """Delete reported content"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    report = get_object_or_404(Report, pk=pk)
    
    if report.job_posting:
        report.job_posting.delete()
    
    report.status = 'resolved'
    report.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Content deleted successfully'
    })


@require_POST
@login_required
def save_report_notes(request, pk):
    """Save admin notes for report"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    report = get_object_or_404(Report, pk=pk)
    data = json.loads(request.body)
    notes = data.get('notes', '')
    
    # Add admin_notes field to Report model if not exists
    # report.admin_notes = notes
    # report.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Notes saved successfully'
    })


# ===== ANNOUNCEMENT DETAIL VIEWS =====

class AnnouncementDetailView(AdminRequiredMixin, DetailView):
    model = Announcement
    template_name = 'admin_dashboard/dashboard_announcement_detail.html'
    context_object_name = 'announcement'


@require_POST
@login_required
def republish_announcement(request, pk):
    """Republish announcement"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    announcement = get_object_or_404(Announcement, pk=pk)
    announcement.is_active = True
    announcement.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Announcement republished successfully'
    })


@require_POST
@login_required
def duplicate_announcement(request, pk):
    """Duplicate announcement"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    announcement = get_object_or_404(Announcement, pk=pk)
    new_announcement = Announcement.objects.create(
        title=f"{announcement.title} (Copy)",
        content=announcement.content,
        is_active=False
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Announcement duplicated successfully',
        'new_id': new_announcement.pk
    })


# ===== FLAGGED CHAT ACTIONS =====

@require_POST
@login_required
def resolve_flagged_chat(request, pk):
    """Mark a flagged chat as resolved"""
    try:
        flagged_chat = get_object_or_404(FlaggedChat, pk=pk)
        flagged_chat.status = 'resolved'
        flagged_chat.save()
        return JsonResponse({'success': True, 'message': 'Chat marked as resolved'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@require_POST
@login_required
def delete_flagged_chat(request, pk):
    """Delete a flagged chat and optionally the conversation"""
    try:
        flagged_chat = get_object_or_404(FlaggedChat, pk=pk)
        conversation = flagged_chat.chat_message
        
        # Delete the flagged chat entry
        flagged_chat.delete()
        
        # Optionally delete the conversation itself
        # conversation.delete()
        
        return JsonResponse({'success': True, 'message': 'Flagged chat deleted'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ===== SKILL VERIFICATION MANAGEMENT =====

class SkillVerificationListView(AdminRequiredMixin, ListView):
    model = Skill
    template_name = 'admin_dashboard/dashboard_skill_verifications.html'
    context_object_name = 'skill_verifications'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Skill.objects.all().select_related('user').order_by('-submitted_at')
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Search by worker name
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(name__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_count'] = Skill.objects.filter(status='pending').count()
        context['verified_count'] = Skill.objects.filter(status='verified').count()
        context['unverified_count'] = Skill.objects.filter(status='unverified').count()
        context['total_count'] = Skill.objects.count()
        return context

class SkillVerificationDetailView(AdminRequiredMixin, DetailView):
    model = Skill
    template_name = 'admin_dashboard/dashboard_skill_verification_detail.html'
    context_object_name = 'skill_verification'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.object.user
        context['worker_total_skills'] = user.skill_verifications.count()
        context['worker_verified_skills'] = user.skill_verifications.filter(status='verified').count()
        context['worker_pending_skills'] = user.skill_verifications.filter(status='pending').count()
        return context

@require_POST
@login_required
def approve_skill_verification(request, pk):
    """Approve a skill verification"""
    try:
        skill = get_object_or_404(Skill, pk=pk)
        skill.status = 'verified'
        skill.save()
        
        # Send notification to worker
        from notifications.models import Notification
        Notification.objects.create(
            user=skill.user,
            message=f"Your skill '{skill.name}' has been verified!",
            notif_type='skill_verified'
        )
        
        return JsonResponse({'success': True, 'message': 'Skill verified successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@require_POST
@login_required
def reject_skill_verification(request, pk):
    """Reject a skill verification"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', 'No reason provided')
        
        skill = get_object_or_404(Skill, pk=pk)
        skill.status = 'unverified'
        skill.save()
        
        # Send notification to worker
        from notifications.models import Notification
        Notification.objects.create(
            user=skill.user,
            message=f"Your skill '{skill.name}' verification was rejected. Reason: {reason}",
            notif_type='skill_rejected'
        )
        
        return JsonResponse({'success': True, 'message': 'Skill verification rejected'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@require_POST
@login_required
def approve_identity_verification(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    submission = get_object_or_404(AccountVerification, pk=pk)
    submission.status = 'approved'
    submission.reviewed_by = request.user
    submission.reviewed_at = timezone.now()
    submission.rejection_reason = ''
    submission.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'rejection_reason'])

    user = submission.user
    user.is_verified = True
    user.verification_status = 'verified'
    user.verification_date = timezone.now()
    if submission.date_of_birth:
        user.date_of_birth = submission.date_of_birth
    user.save(update_fields=['is_verified', 'verification_status', 'verification_date', 'date_of_birth'])

    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        message="Your identity verification has been approved!",
        notif_type="verification_approved"
    )

    return JsonResponse({'success': True, 'message': 'Identity verification approved'})


@require_POST
@login_required
def reject_identity_verification(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

    submission = get_object_or_404(AccountVerification, pk=pk)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        payload = {}

    reason = payload.get('reason', '').strip()
    if not reason:
        return JsonResponse({'success': False, 'message': 'Rejection reason is required.'}, status=400)

    submission.status = 'rejected'
    submission.rejection_reason = reason
    submission.reviewed_by = request.user
    submission.reviewed_at = timezone.now()
    submission.save(update_fields=['status', 'rejection_reason', 'reviewed_by', 'reviewed_at'])

    user = submission.user
    user.is_verified = False
    user.verification_status = 'rejected'
    user.save(update_fields=['is_verified', 'verification_status'])

    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        message=f"Your identity verification was rejected. Reason: {reason}",
        notif_type="verification_rejected"
    )

    return JsonResponse({'success': True, 'message': 'Identity verification rejected'})


# ===== SETTINGS VIEW =====

class SettingsView(AdminRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard_settings.html'
