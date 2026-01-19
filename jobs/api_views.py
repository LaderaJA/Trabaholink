from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from .models import Job, JobApplication, JobOffer, Contract, ProgressLog, JobCategory, JobProgress, Feedback
from .serializers import (
    JobListSerializer, JobDetailSerializer, JobApplicationSerializer,
    JobOfferSerializer, ContractSerializer, ProgressLogSerializer,
    DashboardStatsSerializer, JobCategorySerializer, JobProgressSerializer, FeedbackSerializer
)
from notifications.models import Notification


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Job CRUD operations
    """
    queryset = Job.objects.filter(is_active=True).select_related('owner', 'category')
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'municipality', 'barangay']
    ordering_fields = ['created_at', 'budget', 'title']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return JobListSerializer
        return JobDetailSerializer
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Get all applications for a specific job"""
        job = self.get_object()
        if job.owner != request.user:
            return Response(
                {'error': 'You do not have permission to view applications for this job'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        applications = job.applications.all()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        # Search by worker name
        search = request.query_params.get('search')
        if search:
            applications = applications.filter(
                Q(worker__username__icontains=search) |
                Q(worker__first_name__icontains=search) |
                Q(worker__last_name__icontains=search)
            )
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(applications, request)
        serializer = JobApplicationSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_jobs(self, request):
        """Get jobs posted by the current user"""
        jobs = Job.objects.filter(owner=request.user).select_related('category')
        
        # Filter by status
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            jobs = jobs.filter(is_active=is_active.lower() == 'true')
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(jobs, request)
        serializer = JobListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class JobApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for JobApplication CRUD operations
    """
    queryset = JobApplication.objects.all().select_related('job', 'worker')
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Workers see their own applications, employers see applications to their jobs
        return JobApplication.objects.filter(
            Q(worker=user) | Q(job__owner=user)
        ).select_related('job', 'worker').distinct()
    
    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Get applications submitted by the current user"""
        applications = JobApplication.objects.filter(worker=request.user).select_related('job')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(applications, request)
        serializer = JobApplicationSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def shortlist(self, request, pk=None):
        """Shortlist an application"""
        application = self.get_object()
        
        if application.job.owner != request.user:
            return Response(
                {'error': 'Only the job owner can shortlist applications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        application.is_shortlisted = True
        application.status = "Shortlisted"
        application.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=application.worker,
            message=f"Your application for '{application.job.title}' has been shortlisted!",
            notif_type="application",
            object_id=application.pk
        )
        
        serializer = JobApplicationSerializer(application, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject an application"""
        application = self.get_object()
        
        if application.job.owner != request.user:
            return Response(
                {'error': 'Only the job owner can reject applications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        application.status = "Rejected"
        application.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=application.worker,
            message=f"Your application for '{application.job.title}' has been reviewed.",
            notif_type="application",
            object_id=application.pk
        )
        
        serializer = JobApplicationSerializer(application, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw an application"""
        application = self.get_object()
        
        if application.worker != request.user:
            return Response(
                {'error': 'You can only withdraw your own applications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if application.status in ['Accepted', 'Offer Sent']:
            return Response(
                {'error': 'Cannot withdraw application at this stage'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = "Withdrawn"
        application.save()
        
        # Send notification to employer
        Notification.objects.create(
            user=application.job.owner,
            message=f"{application.worker.username} withdrew their application for '{application.job.title}'",
            notif_type="application",
            object_id=application.pk
        )
        
        serializer = JobApplicationSerializer(application, context={'request': request})
        return Response(serializer.data)


class JobOfferViewSet(viewsets.ModelViewSet):
    """
    ViewSet for JobOffer CRUD operations
    """
    queryset = JobOffer.objects.all().select_related('job', 'employer', 'worker', 'application')
    serializer_class = JobOfferSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Users see offers they sent or received
        return JobOffer.objects.filter(
            Q(employer=user) | Q(worker=user)
        ).select_related('job', 'employer', 'worker', 'application')
    
    def perform_create(self, serializer):
        """Create a job offer"""
        application = serializer.validated_data['application']
        
        # Verify the user is the job owner
        if application.job.owner != self.request.user:
            raise serializers.ValidationError("You can only send offers for your own jobs")
        
        # Check if offer already exists
        if hasattr(application, 'offer'):
            raise serializers.ValidationError("An offer has already been sent for this application")
        
        # Set expiration date (7 days from now)
        expires_at = timezone.now() + timedelta(days=7)
        
        offer = serializer.save(expires_at=expires_at)
        
        # Update application status
        application.status = "Offer Sent"
        application.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=offer.worker,
            message=f"You received a job offer for '{offer.job.title}'. Click to view details.",
            notif_type="contract_draft_update",
            object_id=offer.pk
        )
    
    @action(detail=False, methods=['get'])
    def sent(self, request):
        """Get offers sent by the current user"""
        offers = JobOffer.objects.filter(employer=request.user).select_related('job', 'worker')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            offers = offers.filter(status=status_filter)
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(offers, request)
        serializer = JobOfferSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def received(self, request):
        """Get offers received by the current user"""
        offers = JobOffer.objects.filter(worker=request.user).select_related('job', 'employer')
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            offers = offers.filter(status=status_filter)
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(offers, request)
        serializer = JobOfferSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a job offer"""
        offer = self.get_object()
        
        if offer.worker != request.user:
            return Response(
                {'error': 'Only the worker can accept this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if offer.status != "Pending":
            return Response(
                {'error': 'This offer is no longer available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if offer.is_expired():
            return Response(
                {'error': 'This offer has expired'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Accept the offer and capture the created contract
        contract = offer.accept_offer()
        
        # Send notification to employer
        if contract:
            Notification.objects.create(
                user=offer.employer,
                message=f"{offer.worker.username} accepted your offer for '{offer.job.title}'!",
                notif_type="contract",
                object_id=contract.pk
            )
        
        serializer = JobOfferSerializer(offer, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a job offer"""
        offer = self.get_object()
        
        if offer.worker != request.user:
            return Response(
                {'error': 'Only the worker can reject this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if offer.status != "Pending":
            return Response(
                {'error': 'This offer is no longer available'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        offer.reject_offer(reason)
        
        # Send notification to employer
        Notification.objects.create(
            user=offer.employer,
            message=f"{offer.worker.username} declined your offer for '{offer.job.title}'.",
            notif_type="contract_draft_update",
            object_id=offer.pk
        )
        
        serializer = JobOfferSerializer(offer, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def counter_offer(self, request, pk=None):
        """Send a counter offer"""
        offer = self.get_object()
        
        if offer.worker != request.user:
            return Response(
                {'error': 'Only the worker can send a counter offer'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if offer.status != "Pending":
            return Response(
                {'error': 'Cannot counter this offer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        counter_rate = request.data.get('counter_offer_rate')
        counter_message = request.data.get('counter_offer_message', '')
        
        if not counter_rate:
            return Response(
                {'error': 'Counter offer rate is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        offer.counter_offer_rate = counter_rate
        offer.counter_offer_message = counter_message
        offer.save()
        
        # Send notification to employer
        Notification.objects.create(
            user=offer.employer,
            message=f"{offer.worker.username} sent a counter offer for '{offer.job.title}'. Click to review.",
            notif_type="contract_draft_update",
            object_id=offer.pk
        )
        
        serializer = JobOfferSerializer(offer, context={'request': request})
        return Response(serializer.data)


class ContractViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Contract CRUD operations
    """
    queryset = Contract.objects.all().select_related('job', 'worker', 'client')
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Users see contracts they're involved in
        return Contract.objects.filter(
            Q(worker=user) | Q(client=user)
        ).select_related('job', 'worker', 'client')
    
    @action(detail=False, methods=['get'])
    def my_contracts(self, request):
        """Get contracts for the current user"""
        contracts = self.get_queryset()
        
        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            contracts = contracts.filter(status=status_filter)
        
        # Filter by role
        role = request.query_params.get('role')
        if role == 'worker':
            contracts = contracts.filter(worker=request.user)
        elif role == 'client':
            contracts = contracts.filter(client=request.user)
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(contracts, request)
        serializer = ContractSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_work(self, request, pk=None):
        """Start work on a contract"""
        contract = self.get_object()
        
        if contract.worker != request.user:
            return Response(
                {'error': 'Only the worker can start work'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "Finalized":
            return Response(
                {'error': 'Contract must be accepted before starting work'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.start_work()
        
        # Send notification to client
        Notification.objects.create(
            user=contract.client,
            message=f"{contract.worker.username} has started work on '{contract.job.title}'.",
            notif_type="contract_update",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete_work(self, request, pk=None):
        """Mark work as complete"""
        contract = self.get_object()
        
        if contract.worker != request.user:
            return Response(
                {'error': 'Only the worker can mark work as complete'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "In Progress":
            return Response(
                {'error': 'Contract must be in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.complete_work()
        
        # Send notification to client
        Notification.objects.create(
            user=contract.client,
            message=f"{contract.worker.username} has submitted work for review on '{contract.job.title}'.",
            notif_type="contract_update",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve_completion(self, request, pk=None):
        """Approve completed work"""
        contract = self.get_object()
        
        if contract.client != request.user:
            return Response(
                {'error': 'Only the client can approve completion'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "Submitted for Review":
            return Response(
                {'error': 'Work must be submitted for review first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.status = "Completed"
        contract.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=contract.worker,
            message=f"Your work on '{contract.job.title}' has been approved!",
            notif_type="contract_update",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def request_revision(self, request, pk=None):
        """Request revision on submitted work"""
        contract = self.get_object()
        
        if contract.client != request.user:
            return Response(
                {'error': 'Only the client can request revisions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "Submitted for Review":
            return Response(
                {'error': 'Work must be submitted for review first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.is_revision_requested = True
        contract.status = "In Progress"
        contract.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=contract.worker,
            message=f"Revision requested for '{contract.job.title}'. Please check the details.",
            notif_type="contract_update",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def request_termination(self, request, pk=None):
        """Request contract termination"""
        contract = self.get_object()
        
        if contract.worker != request.user and contract.client != request.user:
            return Response(
                {'error': 'Only parties involved can request termination'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        if not reason:
            return Response(
                {'error': 'Termination reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.request_termination(request.user, reason)
        
        # Send notification to the other party
        other_user = contract.client if request.user == contract.worker else contract.worker
        Notification.objects.create(
            user=other_user,
            message=f"Termination requested for contract '{contract.job.title}'. Click to review.",
            notif_type="contract_cancel",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def progress_logs(self, request, pk=None):
        """Get progress logs for a contract"""
        contract = self.get_object()
        logs = contract.progress_logs.all().order_by('-timestamp')
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(logs, request)
        serializer = ProgressLogSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def progress_updates(self, request, pk=None):
        """Get progress updates for a contract"""
        contract = self.get_object()
        updates = contract.progress_updates.all().order_by('-created_at')
        
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(updates, request)
        serializer = JobProgressSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def accept_contract(self, request, pk=None):
        """Accept contract terms (for finalization)"""
        contract = self.get_object()
        user = request.user
        
        if user not in [contract.worker, contract.client]:
            return Response(
                {'error': 'You are not authorized to accept this contract'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "Negotiation":
            return Response(
                {'error': 'Contract is not in negotiation phase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mark acceptance
        if user == contract.worker:
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
            
            # Decrement job vacancy
            if contract.job.decrement_vacancy():
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Job {contract.job.id} vacancy decremented via API. Remaining: {contract.job.vacancies}")
            
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
        else:
            # Notify the other party
            other_user = contract.client if user == contract.worker else contract.worker
            Notification.objects.create(
                user=other_user,
                message=f"{'Worker' if user == contract.worker else 'Employer'} has accepted the contract for '{contract.job.title}'. Please review and accept.",
                notif_type="contract_acceptance",
                object_id=contract.pk
            )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """Worker marks job as completed"""
        contract = self.get_object()
        
        if contract.worker != request.user:
            return Response(
                {'error': 'Only the worker can mark work as completed'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "In Progress":
            return Response(
                {'error': 'Contract must be in progress'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.status = "Awaiting Review"
        contract.completed_at = timezone.now()
        contract.save()
        
        # Send notification to client
        Notification.objects.create(
            user=contract.client,
            message=f"{contract.worker.username} has marked '{contract.job.title}' as completed. Please review.",
            notif_type="contract_completed",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def end_job(self, request, pk=None):
        """Employer ends the job"""
        contract = self.get_object()
        
        if contract.client != request.user:
            return Response(
                {'error': 'Only the employer can end the job'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if contract.status != "Awaiting Review":
            return Response(
                {'error': 'Job must be awaiting review'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        contract.status = "Completed"
        contract.save()
        
        # Send notification to worker
        Notification.objects.create(
            user=contract.worker,
            message=f"The employer has marked '{contract.job.title}' as completed. Please leave feedback.",
            notif_type="job_completed",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel_contract(self, request, pk=None):
        """Cancel contract"""
        contract = self.get_object()
        
        if request.user not in [contract.worker, contract.client]:
            return Response(
                {'error': 'Only parties involved can cancel the contract'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reason = request.data.get('reason', '')
        
        # Store the old status before changing it
        old_status = contract.status
        
        contract.status = "Cancelled"
        contract.termination_requested_by = request.user
        contract.termination_reason = reason
        contract.termination_requested_at = timezone.now()
        contract.save()
        
        # If contract was finalized, increment vacancy to reopen position
        if old_status in ['Finalized', 'In Progress', 'Awaiting Review']:
            contract.job.increment_vacancy()
        
        # Notify the other party
        other_user = contract.client if request.user == contract.worker else contract.worker
        Notification.objects.create(
            user=other_user,
            message=f"Contract for '{contract.job.title}' has been cancelled.",
            notif_type="contract_cancelled",
            object_id=contract.pk
        )
        
        serializer = ContractSerializer(contract, context={'request': request})
        return Response(serializer.data)


class ProgressLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProgressLog CRUD operations
    """
    queryset = ProgressLog.objects.all().select_related('contract', 'updated_by')
    serializer_class = ProgressLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Users see progress logs for their contracts
        return ProgressLog.objects.filter(
            Q(contract__worker=user) | Q(contract__client=user)
        ).select_related('contract', 'updated_by')


class DashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for dashboard statistics
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def employer_stats(self, request):
        """Get statistics for employer dashboard"""
        user = request.user
        
        stats = {
            'total_jobs': Job.objects.filter(owner=user).count(),
            'active_jobs': Job.objects.filter(owner=user, is_active=True).count(),
            'total_applications': JobApplication.objects.filter(job__owner=user, status='Pending').count(),
            'pending_applications': JobApplication.objects.filter(
                job__owner=user, 
                status='Pending'
            ).count(),
            'active_contracts': Contract.objects.filter(
                client=user, 
                status__in=['Accepted', 'In Progress']
            ).count(),
            'completed_contracts': Contract.objects.filter(
                client=user, 
                status='Completed'
            ).count(),
            'total_offers_sent': JobOffer.objects.filter(employer=user).count(),
            'pending_offers': JobOffer.objects.filter(
                employer=user, 
                status='Pending'
            ).count(),
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def worker_stats(self, request):
        """Get statistics for worker dashboard"""
        user = request.user
        
        stats = {
            'total_applications': JobApplication.objects.filter(worker=user).count(),
            'pending_applications': JobApplication.objects.filter(
                worker=user, 
                status='Pending'
            ).count(),
            'active_contracts': Contract.objects.filter(
                worker=user, 
                status__in=['Accepted', 'In Progress']
            ).count(),
            'completed_contracts': Contract.objects.filter(
                worker=user, 
                status='Completed'
            ).count(),
            'total_offers_received': JobOffer.objects.filter(worker=user).count(),
            'pending_offers': JobOffer.objects.filter(
                worker=user, 
                status='Pending'
            ).count(),
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)


class JobCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for JobCategory (read-only)
    """
    queryset = JobCategory.objects.all()
    serializer_class = JobCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class JobProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet for JobProgress CRUD operations
    """
    queryset = JobProgress.objects.all().select_related('contract', 'updated_by')
    serializer_class = JobProgressSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Users see progress updates for their contracts
        return JobProgress.objects.filter(
            Q(contract__worker=user) | Q(contract__client=user)
        ).select_related('contract', 'updated_by')
    
    def perform_create(self, serializer):
        """Create a progress update"""
        contract = serializer.validated_data['contract']
        
        # Only worker can post progress updates
        if contract.worker != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the worker can post progress updates")
        
        progress = serializer.save()
        
        # Send notification to client
        Notification.objects.create(
            user=contract.client,
            message=f"{contract.worker.username} posted a progress update for '{contract.job.title}'.",
            notif_type="progress_update",
            object_id=contract.pk
        )


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Feedback CRUD operations
    """
    queryset = Feedback.objects.all().select_related('contract', 'giver', 'receiver')
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    
    def get_queryset(self):
        user = self.request.user
        # Users see feedback they gave or received
        return Feedback.objects.filter(
            Q(giver=user) | Q(receiver=user)
        ).select_related('contract', 'giver', 'receiver')
    
    def perform_create(self, serializer):
        """Create feedback"""
        contract = serializer.validated_data['contract']
        user = self.request.user
        
        # Verify user is part of the contract
        if user not in [contract.worker, contract.client]:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can only give feedback for contracts you're involved in")
        
        # Check if contract is completed
        if contract.status != "Completed":
            from rest_framework.exceptions import ValidationError
            raise ValidationError("Feedback can only be given for completed contracts")
        
        # Check if user already gave feedback
        if Feedback.objects.filter(contract=contract, giver=user).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError("You have already given feedback for this contract")
        
        feedback = serializer.save()
        
        # Send notification to receiver
        Notification.objects.create(
            user=feedback.receiver,
            message=f"{feedback.giver.username} left you feedback for '{contract.job.title}'.",
            notif_type="feedback",
            object_id=feedback.pk
        )


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.dateparse import parse_datetime

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def schedule_events_api(request):
    """
    API endpoint to get schedule events for calendar.
    Returns contracts and interviews in FullCalendar format.
    """
    user = request.user
    
    # Get date range from query parameters
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    # Parse dates
    start = parse_datetime(start_date) if start_date else None
    end = parse_datetime(end_date) if end_date else None
    
    events = []
    
    # Get user's contracts (for workers)
    if user.role == 'worker':
        contracts = Contract.objects.filter(
            worker=user,
            status__in=['Finalized', 'In Progress', 'Awaiting Review', 'Completed']
        ).select_related('job', 'client')
        
        # Filter by date range if provided
        if start:
            contracts = contracts.filter(end_date__gte=start.date())
        if end:
            contracts = contracts.filter(start_date__lte=end.date())
        
        # Convert to calendar events
        for contract in contracts:
            event_data = contract.get_calendar_event_data()
            if event_data:
                events.append(event_data)
    
    # Get interviews (for both workers and employers)
    from .models import InterviewSchedule
    
    if user.profile.user_type == 'worker':
        # Worker sees interviews where they are the applicant
        interviews = InterviewSchedule.objects.filter(
            application__worker=user,
            status__in=['scheduled', 'rescheduled']
        ).select_related('application__job', 'application__job__owner')
    else:
        # Employer sees interviews for their job postings
        interviews = InterviewSchedule.objects.filter(
            application__job__owner=user,
            status__in=['scheduled', 'rescheduled']
        ).select_related('application__worker', 'application__job')
    
    # Filter interviews by date range
    if start:
        interviews = interviews.filter(scheduled_datetime__gte=start)
    if end:
        interviews = interviews.filter(scheduled_datetime__lte=end)
    
    # Convert interviews to calendar events
    for interview in interviews:
        # Determine the other party's name
        if user.profile.user_type == 'worker':
            other_party = interview.application.job.owner.get_full_name() or interview.application.job.owner.username
            title_prefix = "Interview with"
        else:
            other_party = interview.application.worker.get_full_name() or interview.application.worker.username
            title_prefix = "Interview:"
        
        # Determine URL based on interview type and timing
        from django.utils import timezone
        now = timezone.now()
        time_until_interview = (interview.scheduled_datetime - now).total_seconds() / 60  # minutes
        
        # For video interviews, link directly to join if within 5 minutes
        if interview.interview_type == 'video' and -5 <= time_until_interview <= interview.duration_minutes:
            event_url = f'/interview/{interview.id}/join/'
        else:
            event_url = f'/job_application/{interview.application.id}/'
        
        # Create event data
        event = {
            'id': f'interview_{interview.id}',
            'title': f'{title_prefix} {other_party}',
            'start': interview.scheduled_datetime.isoformat(),
            'end': (interview.scheduled_datetime + timedelta(minutes=interview.duration_minutes)).isoformat(),
            'backgroundColor': '#3b82f6' if interview.interview_type == 'video' else '#8b5cf6' if interview.interview_type == 'phone' else '#f59e0b',
            'borderColor': '#2563eb' if interview.interview_type == 'video' else '#7c3aed' if interview.interview_type == 'phone' else '#d97706',
            'url': event_url,
            'extendedProps': {
                'type': 'interview',
                'interview_type': interview.get_interview_type_display(),
                'interview_id': interview.id,
                'video_room_url': interview.video_room_url if interview.interview_type == 'video' else None,
                'job_title': interview.application.job.title,
                'status': interview.get_status_display(),
                'can_join': -5 <= time_until_interview <= interview.duration_minutes
            }
        }
        events.append(event)
    
    return Response(events)
