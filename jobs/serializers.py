from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Job, JobCategory, JobApplication, JobOffer, Contract, ProgressLog, JobImage, JobProgress, Feedback

CustomUser = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user info for nested serialization"""
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile_picture_url', 'job_title', 'bio']
    
    def get_profile_picture_url(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        return None


class JobCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = JobCategory
        fields = ['id', 'name']


class JobImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = JobImage
        fields = ['id', 'image', 'image_url']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class JobListSerializer(serializers.ModelSerializer):
    """Serializer for job list view"""
    owner = UserBasicSerializer(read_only=True)
    category = JobCategorySerializer(read_only=True)
    applications_count = serializers.SerializerMethodField()
    distance_km = serializers.FloatField(read_only=True, required=False)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'category', 'budget', 'owner',
            'municipality', 'barangay', 'is_active', 'created_at', 'updated_at',
            'urgency', 'number_of_workers', 'applications_count', 'distance_km',
            'start_datetime', 'duration', 'schedule'
        ]
    
    def get_applications_count(self, obj):
        return obj.applications.count()


class JobDetailSerializer(serializers.ModelSerializer):
    """Detailed job serializer"""
    owner = UserBasicSerializer(read_only=True)
    category = JobCategorySerializer(read_only=True)
    images = JobImageSerializer(source='jobimage_set', many=True, read_only=True)
    applications_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = '__all__'
    
    def get_applications_count(self, obj):
        return obj.applications.count()
    
    def get_has_applied(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.applications.filter(worker=request.user).exists()
        return False
    
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.owner == request.user
        return False


class JobApplicationSerializer(serializers.ModelSerializer):
    """Serializer for job applications"""
    worker = UserBasicSerializer(read_only=True)
    job = JobListSerializer(read_only=True)
    job_id = serializers.PrimaryKeyRelatedField(
        queryset=Job.objects.all(), 
        source='job', 
        write_only=True
    )
    has_offer = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_id', 'worker', 'message', 'cover_letter', 'proposed_rate',
            'available_start_date', 'expected_duration', 'experience',
            'Other_link', 'certifications', 'additional_notes', 'status',
            'applied_at', 'updated_at', 'is_shortlisted', 'employer_notes',
            'has_offer'
        ]
        read_only_fields = ['worker', 'applied_at', 'updated_at']
    
    def get_has_offer(self, obj):
        return hasattr(obj, 'offer')
    
    def create(self, validated_data):
        validated_data['worker'] = self.context['request'].user
        return super().create(validated_data)


class JobOfferSerializer(serializers.ModelSerializer):
    """Serializer for job offers"""
    employer = UserBasicSerializer(read_only=True)
    worker = UserBasicSerializer(read_only=True)
    job = JobListSerializer(read_only=True)
    application = JobApplicationSerializer(read_only=True)
    application_id = serializers.PrimaryKeyRelatedField(
        queryset=JobApplication.objects.all(),
        source='application',
        write_only=True
    )
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = JobOffer
        fields = [
            'id', 'application', 'application_id', 'job', 'employer', 'worker',
            'offered_rate', 'proposed_start_date', 'proposed_end_date',
            'work_schedule', 'message', 'terms_and_conditions', 'status',
            'created_at', 'updated_at', 'expires_at', 'responded_at',
            'rejection_reason', 'counter_offer_rate', 'counter_offer_message',
            'is_expired'
        ]
        read_only_fields = ['employer', 'worker', 'job', 'created_at', 'updated_at', 'responded_at']
    
    def create(self, validated_data):
        application = validated_data['application']
        validated_data['employer'] = self.context['request'].user
        validated_data['worker'] = application.worker
        validated_data['job'] = application.job
        return super().create(validated_data)


class ContractSerializer(serializers.ModelSerializer):
    """Serializer for contracts"""
    worker = UserBasicSerializer(read_only=True)
    client = UserBasicSerializer(read_only=True)
    job = JobListSerializer(read_only=True)
    progress_logs_count = serializers.SerializerMethodField()
    progress_updates_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Contract
        fields = [
            'id', 'job', 'worker', 'client', 'application', 'status', 'payment_status',
            'is_revision_requested', 'job_title', 'job_description', 'agreed_rate',
            'duration', 'schedule', 'start_date', 'notes', 'end_date',
            'scope_of_work', 'payment_terms', 'deliverables',
            'feedback_by_client', 'rating_by_client', 'feedback_by_worker', 'rating_by_worker',
            'created_at', 'updated_at', 'started_at', 'completed_at',
            'finalized_by_worker', 'finalized_by_employer',
            'worker_accepted', 'client_accepted', 'is_finalized', 'is_draft',
            'termination_requested_by', 'termination_reason', 'termination_requested_at',
            'progress_logs_count', 'progress_updates_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'started_at', 'completed_at']
    
    def get_progress_logs_count(self, obj):
        return obj.progress_logs.count()
    
    def get_progress_updates_count(self, obj):
        return obj.progress_updates.count()


class ProgressLogSerializer(serializers.ModelSerializer):
    """Serializer for progress logs"""
    updated_by = UserBasicSerializer(read_only=True)
    contract_id = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all(),
        source='contract',
        write_only=True
    )
    
    class Meta:
        model = ProgressLog
        fields = ['id', 'contract', 'contract_id', 'status', 'message', 'updated_by', 'timestamp']
        read_only_fields = ['updated_by', 'timestamp']
    
    def create(self, validated_data):
        validated_data['updated_by'] = self.context['request'].user
        return super().create(validated_data)


class JobProgressSerializer(serializers.ModelSerializer):
    """Serializer for job progress updates"""
    updated_by = UserBasicSerializer(read_only=True)
    contract_id = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all(),
        source='contract',
        write_only=True
    )
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = JobProgress
        fields = ['id', 'contract', 'contract_id', 'update_text', 'image', 'image_url', 'created_at', 'updated_by']
        read_only_fields = ['updated_by', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None
    
    def create(self, validated_data):
        validated_data['updated_by'] = self.context['request'].user
        return super().create(validated_data)


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for feedback and ratings"""
    giver = UserBasicSerializer(read_only=True)
    receiver = UserBasicSerializer(read_only=True)
    contract_id = serializers.PrimaryKeyRelatedField(
        queryset=Contract.objects.all(),
        source='contract',
        write_only=True
    )
    
    class Meta:
        model = Feedback
        fields = ['id', 'contract', 'contract_id', 'giver', 'receiver', 'rating', 'message', 'created_at']
        read_only_fields = ['giver', 'receiver', 'created_at']
    
    def create(self, validated_data):
        contract = validated_data['contract']
        giver = self.context['request'].user
        
        # Determine receiver based on who is giving feedback
        if giver == contract.worker:
            receiver = contract.client
        else:
            receiver = contract.worker
        
        validated_data['giver'] = giver
        validated_data['receiver'] = receiver
        return super().create(validated_data)


class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_jobs = serializers.IntegerField()
    active_jobs = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    active_contracts = serializers.IntegerField()
    completed_contracts = serializers.IntegerField()
    total_offers_sent = serializers.IntegerField(required=False)
    total_offers_received = serializers.IntegerField(required=False)
    pending_offers = serializers.IntegerField(required=False)
