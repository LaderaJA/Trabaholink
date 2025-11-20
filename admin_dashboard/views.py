from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from datetime import datetime, timedelta
import json

from reports.models import Report
from .models import FlaggedChat, ModeratedWord
from .forms import ModeratedWordForm, AdminCreationForm
from users.models import CustomUser, AccountVerification, Skill, VerificationLog
from jobs.models import Job, JobApplication
from services.models import ServicePost
from announcements.models import Announcement
from announcements.forms import AnnouncementForm
from messaging.models import Conversation
from django import forms


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
        
        # Report categories - count by type (User vs Post)
        user_reports_count = Report.objects.filter(reported_user__isnull=False).count()
        post_reports_count = Report.objects.filter(reported_post__isnull=False).count()
        
        context['report_categories_labels'] = json.dumps(['User Reports', 'Post Reports'])
        context['report_categories_data'] = json.dumps([user_reports_count, post_reports_count])

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
            Q(reporter=user) | Q(reported_user=user)
        )[:10]
        context['user_reports_count'] = Report.objects.filter(
            Q(reporter=user) | Q(reported_user=user)
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
            from reports.models import Report as NewReport
            from jobs.models import Job
            
            data = request.POST
            report_type = data.get("report_type")
            reason = data.get("content", "").strip()
            user_id = data.get("user_id")
            job_id = data.get("job_id")
            screenshot = request.FILES.get('screenshot')

            if not reason:
                return JsonResponse({"success": False, "message": "Report reason cannot be empty."})

            # Validate that either user or job is selected (not both)
            if not user_id and not job_id:
                return JsonResponse({"success": False, "message": "Please select a user or job posting to report."})
            
            if user_id and job_id:
                return JsonResponse({"success": False, "message": "You can only report either a user OR a job posting, not both."})

            # Create the new report
            report_data = {
                'reporter': request.user,
                'reason': reason,
                'status': 'pending',
                'screenshot': screenshot
            }
            
            # Handle user report
            if user_id:
                try:
                    reported_user = CustomUser.objects.get(id=user_id)
                    report_data['reported_user'] = reported_user
                except CustomUser.DoesNotExist:
                    return JsonResponse({"success": False, "message": "User not found."})
            
            # Handle job report
            if job_id:
                try:
                    reported_job = Job.objects.get(id=job_id)
                    report_data['reported_post'] = reported_job
                except Job.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Job posting not found."})
            
            # Create the report
            report = NewReport.objects.create(**report_data)

            return JsonResponse({"success": True, "message": "Report submitted successfully. Our team will review it shortly."})
        except Exception as e:
            print("Error saving report:", e)
            import traceback
            traceback.print_exc()
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

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

        user_ids = list(base_queryset.values_list("user_id", flat=True))
        latest_logs = {}
        if user_ids:
            for log in (
                VerificationLog.objects.filter(user_id__in=user_ids)
                .order_by("user_id", "-created_at")
            ):
                if log.user_id not in latest_logs:
                    latest_logs[log.user_id] = log
        context["verification_logs"] = latest_logs

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


class UserVerificationDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Detailed view of a single verification request with OCR and face matching results"""
    model = AccountVerification
    template_name = "admin_dashboard/user_verification_detail.html"
    context_object_name = "verification"
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        verification = self.get_object()
        
        # Get the latest verification log for this user
        latest_log = VerificationLog.objects.filter(
            user=verification.user
        ).order_by('-created_at').first()
        
        context['verification_log'] = latest_log
        
        # Parse extracted data if available
        if latest_log and latest_log.extracted_data:
            # The extracted_data contains OCR results directly from the pipeline
            # Structure: {raw_text, id_type, full_name, date_of_birth, id_number, address, sex, nationality, qr_data}
            extracted = latest_log.extracted_data
            
            # Separate OCR data (text extracted from ID) with clear field identification
            ocr_fields = {}
            if 'raw_text' in extracted:
                ocr_fields['raw_text'] = extracted['raw_text']
            
            # Name field with source info
            if 'full_name' in extracted:
                ocr_fields['full_name'] = extracted['full_name']
                ocr_fields['full_name_label'] = 'Full Name (from ID)'
                if 'name_source' in extracted:
                    ocr_fields['full_name_source'] = extracted['name_source']
            
            # Date of birth with source info
            if 'date_of_birth' in extracted:
                ocr_fields['date_of_birth'] = extracted['date_of_birth']
                ocr_fields['date_of_birth_label'] = 'Date of Birth (from ID)'
                if 'dob_source' in extracted:
                    ocr_fields['date_of_birth_source'] = extracted['dob_source']
            
            # ID Number / PCN with source info
            if 'id_number' in extracted:
                ocr_fields['id_number'] = extracted['id_number']
                ocr_fields['id_number_label'] = 'PhilSys Card Number (PCN)'
                if 'pcn_source' in extracted:
                    ocr_fields['id_number_source'] = extracted['pcn_source']
            elif 'pcn' in extracted:
                ocr_fields['id_number'] = extracted['pcn']
                ocr_fields['id_number_label'] = 'PhilSys Card Number (PCN)'
            
            # Address with source info
            if 'address' in extracted:
                ocr_fields['address'] = extracted['address']
                ocr_fields['address_label'] = 'Address (from ID)'
                if 'address_source' in extracted:
                    ocr_fields['address_source'] = extracted['address_source']
            
            # Sex/Gender
            if 'sex' in extracted:
                ocr_fields['sex'] = extracted['sex']
                ocr_fields['sex_label'] = 'Sex (from ID)'
                if 'sex_source' in extracted:
                    ocr_fields['sex_source'] = extracted['sex_source']
            
            # Nationality
            if 'nationality' in extracted:
                ocr_fields['nationality'] = extracted['nationality']
                ocr_fields['nationality_label'] = 'Nationality (from ID)'
            
            # ID Type
            if 'id_type' in extracted:
                ocr_fields['id_type'] = extracted['id_type']
            
            # Extraction quality and metadata
            if 'extraction_quality' in extracted:
                ocr_fields['extraction_quality'] = extracted['extraction_quality']
            if 'fields_extracted_count' in extracted:
                ocr_fields['fields_extracted_count'] = extracted['fields_extracted_count']
            
            context['ocr_data'] = ocr_fields if ocr_fields else None
            
            # QR code data
            if 'qr_data' in extracted:
                context['qr_data'] = {'data': extracted['qr_data']}
            else:
                context['qr_data'] = None
            
            # Face matching data (from similarity_score and notes)
            if latest_log.similarity_score is not None:
                # Try to extract method from notes
                method = 'opencv'  # default
                algorithm = 'Histogram Correlation'
                if latest_log.notes and 'face_recognition' in latest_log.notes.lower():
                    method = 'face_recognition'
                    algorithm = 'Deep Learning CNN (dlib)'
                
                context['face_match_data'] = {
                    'similarity': latest_log.similarity_score,
                    'match': latest_log.similarity_score >= 0.6,
                    'method': method,
                    'algorithm': algorithm,
                    'confidence': round(latest_log.similarity_score * 100, 2)
                }
            else:
                context['face_match_data'] = None
            
            # Any remaining metadata
            metadata = {k: v for k, v in extracted.items() 
                       if k not in ['raw_text', 'full_name', 'date_of_birth', 'id_number', 
                                    'address', 'sex', 'nationality', 'id_type', 'qr_data']}
            context['verification_metadata'] = metadata if metadata else None
        
        # Get all verification logs for history
        context['verification_history'] = VerificationLog.objects.filter(
            user=verification.user
        ).order_by('-created_at')[:10]
        
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
        except (AttributeError, ValueError) as e:
            logger.warning(f"Error fetching applicants: {e}")
            context['applicants'] = []
            context['applicants_count'] = 0
        context['related_reports'] = Report.objects.filter(reported_post=self.object)
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
        reporter=request.user,
        reported_post=job,
        reason=reason,
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
        context['worker_services_count'] = self.object.worker.service_posts.count()
        context['worker_rating'] = None  # Add rating calculation if available
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
def save_service_notes(request, pk):
    """Save admin notes for service"""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    
    service = get_object_or_404(ServicePost, pk=pk)
    data = json.loads(request.body)
    notes = data.get('notes', '')
    
    service.admin_notes = notes
    service.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Notes saved successfully'
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
    
    if report.reported_post:
        report.reported_post.delete()
    
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
    
    report.admin_notes = notes
    report.save()
    
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
    user.identity_verification_status = 'verified'
    user.verification_date = timezone.now()
    if submission.date_of_birth:
        user.date_of_birth = submission.date_of_birth
    user.save(update_fields=['is_verified', 'verification_status', 'identity_verification_status', 'verification_date', 'date_of_birth'])

    latest_log = user.verification_logs.order_by('-created_at').first()
    VerificationLog.objects.create(
        user=user,
        extracted_data=latest_log.extracted_data if latest_log else {},
        similarity_score=user.verification_score,
        process_type='manual',
        result='verified',
        notes=f"Manually approved by {request.user.username}",
    )

    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        message="Your identity verification has been approved! You now have access to all platform features.",
        notif_type="verification_approved"
    )
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Verification approved for user {user.id} ({user.username}) by {request.user.username}. Notification created.")

    return JsonResponse({
        'success': True, 
        'message': 'Identity verification approved',
        'user_id': user.id,
        'notification_sent': True
    })


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

    # Refresh user from database to avoid stale data
    user = CustomUser.objects.get(pk=submission.user.pk)
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Before update - User {user.id} verification_status: {user.verification_status}, is_verified: {user.is_verified}")
    
    user.is_verified = False
    user.verification_status = 'failed'
    user.identity_verification_status = 'rejected'
    user.verification_date = None  # Clear verification date
    user.save(update_fields=['is_verified', 'verification_status', 'identity_verification_status', 'verification_date'])
    
    # Force refresh from database to confirm save
    user.refresh_from_db()
    logger.info(f"After update - User {user.id} verification_status: {user.verification_status}, is_verified: {user.is_verified}")

    latest_log = user.verification_logs.order_by('-created_at').first()
    VerificationLog.objects.create(
        user=user,
        extracted_data=latest_log.extracted_data if latest_log else {},
        similarity_score=user.verification_score,
        process_type='manual',
        result='failed',
        notes=f"Rejected by {request.user.username}: {reason}",
    )

    from notifications.models import Notification
    Notification.objects.create(
        user=user,
        message=f"❌ Your identity verification was rejected by {request.user.get_full_name() or request.user.username}. Reason: {reason}. Please review the feedback carefully and submit a new verification request with the required corrections.",
        notif_type="verification_rejected"
    )
    
    logger.info(f"Verification rejected for user {user.id} ({user.username}) by {request.user.username}. Notification created. Final status: {user.verification_status}")

    return JsonResponse({
        'success': True, 
        'message': 'Identity verification rejected',
        'user_id': user.id,
        'username': user.username,
        'verification_status': user.verification_status,
        'is_verified': user.is_verified,
        'notification_sent': True
    })


@login_required
def check_verification_progress(request, user_id):
    """Check the progress of a verification task."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    from users.services.verification.progress_tracker import VerificationProgressTracker
    
    progress = VerificationProgressTracker.get_progress(user_id)
    
    if progress:
        return JsonResponse({
            'success': True,
            'progress': progress
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'No active verification found'
        })


@login_required
@require_POST
def reprocess_verification(request, pk):
    """Re-process verification using the new redesigned verification system."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        user = verification.user
        
        # Check if user has images
        if not user.id_image or not user.selfie_image:
            return JsonResponse({
                'success': False,
                'message': 'User has no ID or selfie images uploaded'
            }, status=400)
        
        # Trigger the new redesigned verification task (async)
        from users.tasks import run_verification_pipeline
        
        # Run asynchronously - returns immediately, progress tracked via Redis
        task = run_verification_pipeline.delay(user.id, verification.id)
        
        return JsonResponse({
            'success': True,
            'message': 'Verification processing started. Watch the progress indicator.',
            'task_id': task.id,
            'user_id': user.id
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed to reprocess verification {pk}: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error re-processing verification: {str(e)}'
        }, status=500)


@login_required
@require_POST
def verify_philsys_qr(request, pk):
    """Upload ID back image directly to PhilSys government portal using Playwright."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)
    
    try:
        verification = AccountVerification.objects.get(pk=pk)
        user = verification.user
        
        # Check if verification has ID back image
        if not verification.id_image_back:
            return JsonResponse({
                'success': False,
                'message': 'No ID back image found. PhilSys verification requires the back of the ID.'
            }, status=400)
        
        # Get absolute path to ID back image
        import os
        from django.conf import settings
        
        id_back_path = verification.id_image_back.path
        
        if not os.path.exists(id_back_path):
            return JsonResponse({
                'success': False,
                'message': 'ID back image file not found on server.'
            }, status=400)
        
        # Use Playwright to upload image to PhilSys portal
        from playwright.sync_api import sync_playwright
        from users.models import VerificationLog
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Starting PhilSys verification for user {user.id} using Playwright")
        
        verification_result = {
            'verified': False,
            'reason': 'Unknown error',
            'pcn': None,
            'name': None,
            'screenshot': None
        }
        
        try:
            with sync_playwright() as p:
                # Launch browser (headless mode)
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                logger.info("Navigating to PhilSys verification portal...")
                
                # Navigate to PhilSys verification page with retry logic
                try:
                    page.goto('https://verify.philsys.gov.ph/', wait_until='load', timeout=60000)
                except Exception as e:
                    logger.warning(f"First attempt failed: {e}, retrying with domcontentloaded...")
                    try:
                        page.goto('https://verify.philsys.gov.ph/', wait_until='domcontentloaded', timeout=60000)
                    except Exception as e2:
                        logger.error(f"Navigation failed: {e2}")
                        browser.close()
                        return JsonResponse({
                            'success': False,
                            'message': f'Cannot connect to PhilSys portal. The site may be down or unreachable. Error: {str(e2)}'
                        }, status=503)
                
                # Wait for page to load
                page.wait_for_load_state('domcontentloaded')
                page.wait_for_timeout(2000)
                
                # Step 1: Click the QR scan image to open modal
                logger.info("Step 1: Clicking QR scan image...")
                try:
                    scan_image = page.locator('img[alt="scan-image"].scanImg')
                    if scan_image.count() == 0:
                        # Fallback selector
                        scan_image = page.locator('img[src*="scan2.png"]')
                    
                    scan_image.click()
                    logger.info("✓ QR scan image clicked")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    logger.error(f"Failed to click scan image: {e}")
                    screenshot_path = f'/tmp/philsys_error_{user.id}_step1.png'
                    page.screenshot(path=screenshot_path)
                    verification_result['reason'] = f'Could not click scan image: {str(e)}'
                    browser.close()
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed at step 1: Could not click scan image. Screenshot: {screenshot_path}'
                    }, status=400)
                
                # Step 2: Click "Camera" button in modal
                logger.info("Step 2: Clicking Camera button in modal...")
                try:
                    camera_button = page.locator('button.swal2-confirm:has-text("Camera")')
                    if camera_button.count() == 0:
                        # Fallback selector
                        camera_button = page.locator('button.swal2-confirm.swal2-styled')
                    
                    camera_button.click()
                    logger.info("✓ Camera button clicked")
                    page.wait_for_timeout(2000)
                except Exception as e:
                    logger.error(f"Failed to click Camera button: {e}")
                    screenshot_path = f'/tmp/philsys_error_{user.id}_step2.png'
                    page.screenshot(path=screenshot_path)
                    verification_result['reason'] = f'Could not click Camera button: {str(e)}'
                    browser.close()
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed at step 2: Could not click Camera button. Screenshot: {screenshot_path}'
                    }, status=400)
                
                # Step 3: Click "Scan an Image File" link
                logger.info("Step 3: Clicking 'Scan an Image File' link...")
                try:
                    scan_file_link = page.locator('#reader__dashboard_section_swaplink')
                    if scan_file_link.count() == 0:
                        # Fallback selector
                        scan_file_link = page.locator('a[href="#scan-using-file"]')
                    
                    scan_file_link.click()
                    logger.info("✓ 'Scan an Image File' link clicked")
                    page.wait_for_timeout(1000)
                except Exception as e:
                    logger.error(f"Failed to click 'Scan an Image File' link: {e}")
                    screenshot_path = f'/tmp/philsys_error_{user.id}_step3.png'
                    page.screenshot(path=screenshot_path)
                    verification_result['reason'] = f'Could not click Scan an Image File link: {str(e)}'
                    browser.close()
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed at step 3: Could not click Scan an Image File link. Screenshot: {screenshot_path}'
                    }, status=400)
                
                # Step 4: Upload the ID back image
                logger.info(f"Step 4: Uploading file: {id_back_path}")
                try:
                    upload_input = page.locator('#reader__filescan_input')
                    if upload_input.count() == 0:
                        # Fallback selector
                        upload_input = page.locator('input[type="file"][accept="image/*"]')
                    
                    upload_input.set_input_files(id_back_path)
                    logger.info("✓ File uploaded successfully")
                    
                    # Wait for upload to process and QR code to be scanned
                    page.wait_for_timeout(5000)
                except Exception as e:
                    logger.error(f"Failed to upload file: {e}")
                    screenshot_path = f'/tmp/philsys_error_{user.id}_step4.png'
                    page.screenshot(path=screenshot_path)
                    verification_result['reason'] = f'Could not upload file: {str(e)}'
                    browser.close()
                    return JsonResponse({
                        'success': False,
                        'message': f'Failed at step 4: Could not upload file. Screenshot: {screenshot_path}'
                    }, status=400)
                
                # Check for verification result
                logger.info("Checking for verification result...")
                
                # Look for success/failure indicators
                success_indicators = [
                    '.success',
                    '.verified',
                    '[class*="success"]',
                    'text=/verified/i',
                    'text=/valid/i'
                ]
                
                failure_indicators = [
                    '.error',
                    '.failed',
                    '[class*="error"]',
                    'text=/not found/i',
                    'text=/invalid/i',
                    'text=/failed/i'
                ]
                
                # Check for success
                for selector in success_indicators:
                    try:
                        if page.locator(selector).count() > 0:
                            verification_result['verified'] = True
                            verification_result['reason'] = 'Verified by PhilSys government portal'
                            logger.info("Verification successful!")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} not found or error: {e}")
                        continue
                
                # Check for failure
                if not verification_result['verified']:
                    for selector in failure_indicators:
                        try:
                            if page.locator(selector).count() > 0:
                                error_text = page.locator(selector).first.inner_text()
                                verification_result['reason'] = f'PhilSys verification failed: {error_text}'
                                logger.warning(f"Verification failed: {error_text}")
                                break
                        except Exception as e:
                            logger.debug(f"Error checking failure indicator {selector}: {e}")
                            continue
                
                # Try to extract all PhilSys data from the modal
                try:
                    page_text = page.content()
                    import re
                    
                    # Extract all fields from the modal using regex
                    # Look for patterns like: <strong>Last Name: </strong>VALUE
                    
                    # Try multiple patterns for each field
                    # Pattern 1: <strong>Label: </strong>Value
                    # Pattern 2: <strong>Label:</strong> Value (with space after tag)
                    # Pattern 3: Look in the visible text
                    
                    # Last Name
                    last_name_match = re.search(r'<strong>Last Name:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if last_name_match:
                        verification_result['last_name'] = last_name_match.group(1).strip()
                        logger.info(f"Extracted Last Name: {verification_result['last_name']}")
                    
                    # First Name
                    first_name_match = re.search(r'<strong>First Name:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if first_name_match:
                        verification_result['first_name'] = first_name_match.group(1).strip()
                        logger.info(f"Extracted First Name: {verification_result['first_name']}")
                    
                    # Middle Name
                    middle_name_match = re.search(r'<strong>Middle Name:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if middle_name_match:
                        verification_result['middle_name'] = middle_name_match.group(1).strip()
                        logger.info(f"Extracted Middle Name: {verification_result['middle_name']}")
                    
                    # Suffix
                    suffix_match = re.search(r'<strong>Suffix:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if suffix_match:
                        suffix_value = suffix_match.group(1).strip()
                        if suffix_value and suffix_value.lower() not in ['', 'none', 'n/a']:
                            verification_result['suffix'] = suffix_value
                    
                    # Sex
                    sex_match = re.search(r'<strong>Sex:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if sex_match:
                        verification_result['sex'] = sex_match.group(1).strip()
                        logger.info(f"Extracted Sex: {verification_result['sex']}")
                    
                    # Date of Birth
                    dob_match = re.search(r'<strong>Date of Birth:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if dob_match:
                        verification_result['date_of_birth'] = dob_match.group(1).strip()
                        logger.info(f"Extracted DOB: {verification_result['date_of_birth']}")
                    
                    # Place of Birth
                    pob_match = re.search(r'<strong>Place of Birth:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if pob_match:
                        verification_result['place_of_birth'] = pob_match.group(1).strip()
                        logger.info(f"Extracted Place of Birth: {verification_result['place_of_birth']}")
                    
                    # PCN - try multiple patterns
                    pcn_match = re.search(r'<strong>Philsys Card Number \(PCN\):\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if not pcn_match:
                        pcn_match = re.search(r'<strong>PCN:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if pcn_match:
                        verification_result['pcn'] = pcn_match.group(1).strip()
                        logger.info(f"Extracted PCN: {verification_result['pcn']}")
                    else:
                        # Fallback: Look for PCN pattern anywhere in text
                        pcn_pattern_match = re.search(r'\b(\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b', page_text)
                        if pcn_pattern_match:
                            pcn_raw = pcn_pattern_match.group(1)
                            # Normalize format
                            pcn_digits = re.sub(r'[-\s]', '', pcn_raw)
                            verification_result['pcn'] = f"{pcn_digits[0:4]}-{pcn_digits[4:8]}-{pcn_digits[8:12]}-{pcn_digits[12:16]}"
                            logger.info(f"Extracted PCN (pattern): {verification_result['pcn']}")
                    
                    # Date of Issuance
                    doi_match = re.search(r'<strong>Date of Issuance:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if doi_match:
                        verification_result['date_of_issuance'] = doi_match.group(1).strip()
                        logger.info(f"Extracted Date of Issuance: {verification_result['date_of_issuance']}")
                    
                    # Best Capture Finger
                    finger_match = re.search(r'<strong>Best Capture Finger:\s*</strong>([^<]*)', page_text, re.IGNORECASE)
                    if finger_match:
                        verification_result['best_capture_finger'] = finger_match.group(1).strip()
                        logger.info(f"Extracted Best Capture Finger: {verification_result['best_capture_finger']}")
                    
                    # Construct full name
                    if verification_result.get('first_name') and verification_result.get('last_name'):
                        full_name_parts = [verification_result['last_name'], verification_result['first_name']]
                        if verification_result.get('middle_name'):
                            full_name_parts.append(verification_result['middle_name'])
                        if verification_result.get('suffix'):
                            full_name_parts.append(verification_result['suffix'])
                        verification_result['name'] = ', '.join([full_name_parts[0], ' '.join(full_name_parts[1:])])
                        logger.info(f"Constructed Full Name: {verification_result['name']}")
                    
                except Exception as e:
                    logger.error(f"Error extracting PhilSys data: {e}")
                    pass
                
                # Take screenshot of result
                screenshot_path = f'/tmp/philsys_result_{user.id}.png'
                page.screenshot(path=screenshot_path, full_page=True)
                verification_result['screenshot'] = screenshot_path
                logger.info(f"Screenshot saved to {screenshot_path}")
                
                browser.close()
                
        except Exception as e:
            logger.exception(f"Playwright error during PhilSys verification: {e}")
            verification_result['reason'] = f'Browser automation error: {str(e)}'
        
        # Update verification log
        notes = []
        notes.append(f"PhilSys Web Verification (Manual - Playwright)")
        notes.append(f"Verified: {verification_result['verified']}")
        if verification_result['pcn']:
            notes.append(f"PCN: {verification_result['pcn']}")
        notes.append(f"Reason: {verification_result['reason']}")
        if verification_result['screenshot']:
            notes.append(f"Screenshot: {verification_result['screenshot']}")
        
        # Update or create verification log
        log = VerificationLog.objects.filter(user=user).order_by('-created_at').first()
        
        if log:
            # Update existing log
            log.notes += "\n\n" + "\n".join(notes)
            log.extracted_data = log.extracted_data or {}
            log.extracted_data['philsys_web'] = verification_result
            log.save()
        else:
            # Create new log
            log = VerificationLog.objects.create(
                user=user,
                extracted_data={'philsys_web': verification_result},
                process_type='manual',
                result='verified' if verification_result['verified'] else 'manual_review',
                notes="\n".join(notes)
            )
        
        # Update user PhilSys verification status
        user.is_verified_philsys = verification_result['verified']
        user.save(update_fields=['is_verified_philsys'])
        
        # Send notification to user
        from notifications.models import Notification
        if verification_result['verified']:
            Notification.objects.create(
                user=user,
                message="✅ Your PhilSys ID has been verified with the government portal!",
                notif_type="philsys_verified"
            )
        
        return JsonResponse({
            'success': True,
            'verified': verification_result['verified'],
            'pcn': verification_result['pcn'],
            'name': verification_result['name'],
            'reason': verification_result['reason'] if not verification_result['verified'] else None
        })
        
    except AccountVerification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Verification not found'}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"Failed to verify PhilSys QR for verification {pk}: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error verifying PhilSys QR: {str(e)}'
        }, status=500)


# ===== SETTINGS VIEW =====

class SettingsView(AdminRequiredMixin, TemplateView):
    template_name = 'admin_dashboard/dashboard_settings.html'


# ===== ADMIN MANAGEMENT VIEWS =====

class AdminListView(AdminRequiredMixin, ListView):
    """List all admin users"""
    model = CustomUser
    template_name = 'admin_dashboard/admin_list.html'
    context_object_name = 'admins'
    paginate_by = 20
    
    def get_queryset(self):
        return CustomUser.objects.filter(
            Q(is_staff=True) | Q(is_superuser=True)
        ).order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_admins'] = self.get_queryset().count()
        context['superuser_count'] = CustomUser.objects.filter(is_superuser=True).count()
        context['staff_count'] = CustomUser.objects.filter(is_staff=True, is_superuser=False).count()
        return context


class AdminCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create new admin user - only accessible by superusers"""
    model = CustomUser
    form_class = AdminCreationForm
    template_name = 'admin_dashboard/admin_create.html'
    success_url = reverse_lazy('admin_dashboard:admin_list')
    
    def test_func(self):
        # Only superusers can create new admins
        return self.request.user.is_superuser
    
    def form_valid(self, form):
        from django.contrib import messages
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Admin user "{self.object.username}" created successfully!'
        )
        
        # Log the action
        import logging
        logger = logging.getLogger(__name__)
        logger.info(
            f"New admin created: {self.object.username} (ID: {self.object.id}) "
            f"by {self.request.user.username}"
        )
        
        return response
    
    def handle_no_permission(self):
        from django.contrib import messages
        messages.error(
            self.request,
            'Only superusers can create new admin accounts.'
        )
        return redirect('admin_dashboard:dashboard_main')


class AdminDetailView(AdminRequiredMixin, DetailView):
    """View admin user details"""
    model = CustomUser
    template_name = 'admin_dashboard/admin_detail.html'
    context_object_name = 'admin_user'
    
    def get_queryset(self):
        return CustomUser.objects.filter(Q(is_staff=True) | Q(is_superuser=True))


@require_POST
@login_required
def toggle_admin_status(request, pk):
    """Toggle admin user's active status - superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Only superusers can modify admin accounts'}, status=403)
    
    admin_user = get_object_or_404(CustomUser, pk=pk)
    
    # Prevent deactivating yourself
    if admin_user == request.user:
        return JsonResponse({'success': False, 'message': 'You cannot deactivate your own account'}, status=400)
    
    # Prevent modifying other superusers unless you're also a superuser
    if admin_user.is_superuser and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'You cannot modify superuser accounts'}, status=403)
    
    admin_user.is_active = not admin_user.is_active
    admin_user.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Admin {"activated" if admin_user.is_active else "deactivated"} successfully',
        'is_active': admin_user.is_active
    })


@require_POST
@login_required
def revoke_admin_access(request, pk):
    """Revoke admin access from a user - superuser only"""
    if not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Only superusers can revoke admin access'}, status=403)
    
    admin_user = get_object_or_404(CustomUser, pk=pk)
    
    # Prevent revoking your own access
    if admin_user == request.user:
        return JsonResponse({'success': False, 'message': 'You cannot revoke your own admin access'}, status=400)
    
    # Prevent revoking other superusers
    if admin_user.is_superuser:
        return JsonResponse({'success': False, 'message': 'Cannot revoke access from superusers'}, status=403)
    
    admin_user.is_staff = False
    admin_user.save()
    
    # Send notification
    try:
        from notifications.models import Notification
        Notification.objects.create(
            user=admin_user,
            message="Your admin access has been revoked. Please contact a superuser if you have questions.",
            notif_type="announcement"
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to send notification to {admin_user.username}: {e}")
    
    return JsonResponse({
        'success': True,
        'message': f'Admin access revoked from {admin_user.username}'
    })
