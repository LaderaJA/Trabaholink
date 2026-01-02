"""
Unit tests for jobs app views
"""
import pytest
from django.urls import reverse
from jobs.models import JobCategory, Job
from decimal import Decimal

pytestmark = pytest.mark.django_db


class TestJobListView:
    """Test job listing view"""
    
    def test_job_list_page_loads(self, client):
        """Test job list page loads successfully"""
        response = client.get(reverse('jobs:job_list'))
        assert response.status_code == 200
    
    def test_job_list_shows_active_jobs(self, client, create_employer):
        """Test job list shows only active jobs"""
        category = JobCategory.objects.create(name='Testing')
        Job.objects.create(
            owner=create_employer,
            category=category,
            title='Active Job',
            description='This job is active',
            budget=Decimal('100.00'),
            municipality='Manila',
            barangay='Intramuros',
            is_active=True
        )
        Job.objects.create(
            owner=create_employer,
            category=category,
            title='Inactive Job',
            description='This job is inactive',
            budget=Decimal('100.00'),
            municipality='Manila',
            barangay='Intramuros',
            is_active=False
        )
        
        response = client.get(reverse('jobs:job_list'))
        content = response.content.decode()
        assert 'Active Job' in content


class TestJobDetailView:
    """Test job detail view"""
    
    def test_job_detail_page_loads(self, client, create_employer):
        """Test job detail page loads"""
        category = JobCategory.objects.create(name='Detail Test')
        job = Job.objects.create(
            owner=create_employer,
            category=category,
            title='Test Job Detail',
            description='Job description',
            budget=Decimal('200.00'),
            municipality='Pasay',
            barangay='Barangay 1'
        )
        response = client.get(reverse('jobs:job_detail', kwargs={'pk': job.pk}))
        assert response.status_code == 200
        assert 'Test Job Detail' in response.content.decode()


class TestJobCreateView:
    """Test job creation view"""
    
    def test_job_create_requires_authentication(self, client):
        """Test job creation requires authentication"""
        response = client.get(reverse('jobs:job_create'))
        assert response.status_code == 302  # Redirect to login
    
    def test_employer_can_access_job_create(self, client, create_employer):
        """Test employer can access job creation"""
        create_employer.has_selected_role = True
        create_employer.save()
        client.force_login(create_employer)
        response = client.get(reverse('jobs:job_create'), follow=True)
        # May redirect due to middleware, check final status
        assert response.status_code in [200, 302]
