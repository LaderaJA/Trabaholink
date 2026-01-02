"""Unit tests for jobs app models"""
import pytest
from django.contrib.auth import get_user_model
from jobs.models import JobCategory, Job, JobApplication
from decimal import Decimal
import uuid

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestJobCategoryModel:
    """Test JobCategory model"""
    
    def test_create_job_category(self):
        """Test creating a job category"""
        category = JobCategory.objects.create(name=f'Construction_{uuid.uuid4().hex[:8]}')
        assert 'Construction' in category.name
        assert str(category) == category.name


class TestJobModel:
    """Test Job model"""
    
    def test_create_job(self, create_employer):
        """Test creating a job"""
        category = JobCategory.objects.create(name=f'Carpentry_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Carpenter Needed',
            description='Need experienced carpenter',
            budget=Decimal('1000.00'),
            municipality='Quezon City',
            barangay='Barangay 1'
        )
        assert job.title == 'Carpenter Needed'
        assert job.owner == create_employer
        assert job.is_active
    
    def test_job_string_representation(self, create_employer):
        """Test job __str__ method"""
        category = JobCategory.objects.create(name=f'Painting_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='House Painter',
            description='Paint residential house',
            budget=Decimal('300.00'),
            municipality='Manila',
            barangay='Ermita'
        )
        assert str(job) == f'House Painter - {create_employer.username}'
    
    def test_job_default_status(self, create_employer):
        """Test job default status is active"""
        category = JobCategory.objects.create(name=f'Cleaning_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Cleaner Needed',
            description='Office cleaning',
            budget=Decimal('200.00'),
            municipality='Makati',
            barangay='Poblacion'
        )
        assert job.is_active == True
    
    def test_job_budget_field(self, create_employer):
        """Test job budget field"""
        category = JobCategory.objects.create(name=f'Electrical_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Electrician',
            description='Electrical work',
            budget=Decimal('500.00'),
            municipality='Pasig',
            barangay='Kapitolyo'
        )
        assert job.budget == Decimal('500.00')


class TestJobApplicationModel:
    """Test JobApplication model"""
    
    def test_create_job_application(self, create_worker, create_employer):
        """Test creating a job application"""
        category = JobCategory.objects.create(name=f'Masonry_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Mason Needed',
            description='Building work',
            budget=Decimal('800.00'),
            municipality='Caloocan',
            barangay='Bagong Silang'
        )
        
        application = JobApplication.objects.create(
            job=job,
            worker=create_worker,
            message='I am interested in this job',
        )
        
        assert application.job == job
        assert application.worker == create_worker
        assert application.status == 'Pending'
    
    def test_job_application_status_choices(self, create_worker, create_employer):
        """Test job application status field"""
        category = JobCategory.objects.create(name=f'Roofing_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Roofer',
            description='Roof repair',
            budget=Decimal('600.00'),
            municipality='Taguig',
            barangay='Fort Bonifacio'
        )
        
        application = JobApplication.objects.create(
            job=job,
            worker=create_worker,
            message='Available immediately',
            status='Pending'
        )
        
        assert application.status == 'Pending'
        
        application.status = 'Accepted'
        application.save()
        assert application.status == 'Accepted'
    
    def test_job_application_string(self, create_worker, create_employer):
        """Test job application __str__ method"""
        category = JobCategory.objects.create(name=f'Welding_{uuid.uuid4().hex[:8]}')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Welder Position',
            description='Metal work',
            budget=Decimal('700.00'),
            municipality='Paranaque',
            barangay='BF Homes'
        )
        
        application = JobApplication.objects.create(
            job=job,
            worker=create_worker,
            message='I am a skilled welder',
        )
        
        expected_str = f"{create_worker.username} applied for {job.title}"
        assert str(application) == expected_str
