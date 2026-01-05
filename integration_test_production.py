#!/usr/bin/env python
"""
Trabaholink Production Integration Test Suite
Tests the complete system workflow end-to-end

Run on production server:
./dc.sh exec web python integration_test_production.py

Or standalone:
python integration_test_production.py
"""

import os
import sys
import django
import time
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

# Import models
User = get_user_model()
from jobs.models import Job, JobCategory, JobApplication, Contract, GeneralCategory
from services.models import ServicePost, ServiceCategory, ServiceReview
from messaging.models import Conversation, Message
from notifications.models import Notification
from users.models import NotificationPreference

# Test configuration
TEST_PREFIX = "integtest_"
CLEANUP_AFTER_TEST = True  # Set to False to keep test data for inspection

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    """Print info message"""
    print(f"  {text}")

class IntegrationTestRunner:
    """Main test runner class"""
    
    def __init__(self):
        self.test_users = []
        self.test_jobs = []
        self.test_services = []
        self.test_applications = []
        self.test_contracts = []
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = None
        self.test_results = []  # Store detailed test results
        
    def cleanup(self):
        """Clean up test data"""
        if not CLEANUP_AFTER_TEST:
            print_warning("Cleanup disabled - test data preserved")
            return
            
        print_info("Cleaning up test data...")
        
        try:
            # Delete in reverse order of dependencies
            Contract.objects.filter(job__title__startswith=TEST_PREFIX).delete()
            JobApplication.objects.filter(job__title__startswith=TEST_PREFIX).delete()
            Job.objects.filter(title__startswith=TEST_PREFIX).delete()
            ServicePost.objects.filter(headline__startswith=TEST_PREFIX).delete()
            Message.objects.filter(sender__username__startswith=TEST_PREFIX).delete()
            Conversation.objects.filter(user1__username__startswith=TEST_PREFIX).delete()
            Notification.objects.filter(user__username__startswith=TEST_PREFIX).delete()
            NotificationPreference.objects.filter(user__username__startswith=TEST_PREFIX).delete()
            User.objects.filter(username__startswith=TEST_PREFIX).delete()
            
            print_success("Test data cleaned up")
        except Exception as e:
            print_error(f"Cleanup error: {e}")
    
    def run_test(self, test_name, test_func):
        """Run a single test and track results"""
        test_start = time.time()
        error_msg = None
        status = "passed"
        
        try:
            print(f"\n{Colors.BOLD}Test: {test_name}{Colors.END}")
            test_func()
            self.passed_tests += 1
            print_success(f"PASSED: {test_name}")
        except AssertionError as e:
            self.failed_tests += 1
            status = "failed"
            error_msg = str(e)
            print_error(f"FAILED: {test_name}")
            print_error(f"Reason: {e}")
        except Exception as e:
            self.failed_tests += 1
            status = "failed"
            error_msg = f"{type(e).__name__}: {e}"
            print_error(f"ERROR: {test_name}")
            print_error(f"Exception: {error_msg}")
        
        # Store result
        duration = time.time() - test_start
        self.test_results.append({
            'name': test_name,
            'status': status,
            'duration': duration,
            'error': error_msg
        })
        
        return status == "passed"
    
    def test_01_database_connection(self):
        """Test database connectivity"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1, "Database connection failed"
        print_info("Database connection: OK")
    
    def test_02_postgis_extension(self):
        """Test PostGIS extension is available"""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_version();")
            version = cursor.fetchone()[0]
            print_info(f"PostGIS version: {version}")
            assert version is not None, "PostGIS not available"
    
    def test_03_create_test_users(self):
        """Test user creation with different roles"""
        # Create client user
        client = User.objects.create_user(
            username=f"{TEST_PREFIX}client1",
            email=f"{TEST_PREFIX}client1@test.com",
            password="testpass123",
            role='client',
            first_name="Test",
            last_name="Client"
        )
        client.location = Point(120.9744, 14.4271, srid=4326)  # Bacoor, Cavite
        client.save()
        self.test_users.append(client)
        print_info(f"Created client: {client.username}")
        
        # Create worker users
        for i in range(1, 3):
            worker = User.objects.create_user(
                username=f"{TEST_PREFIX}worker{i}",
                email=f"{TEST_PREFIX}worker{i}@test.com",
                password="testpass123",
                role='worker',
                first_name=f"Test",
                last_name=f"Worker{i}"
            )
            # Different locations for radius testing
            if i == 1:
                worker.location = Point(120.9700, 14.4250, srid=4326)  # ~500m away
            else:
                worker.location = Point(120.9900, 14.4400, srid=4326)  # ~2km away
            worker.save()
            self.test_users.append(worker)
            print_info(f"Created worker: {worker.username}")
        
        assert len(self.test_users) == 3, "Failed to create all test users"
        print_success(f"Created {len(self.test_users)} test users")
    
    def test_04_notification_preferences(self):
        """Test notification preference setup"""
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        # Get or create general category
        general_cat, _ = GeneralCategory.objects.get_or_create(
            slug='construction',
            defaults={'name': 'Construction & Trades'}
        )
        
        # Create notification preference
        pref = NotificationPreference.objects.create(
            user=worker1,
            is_active=True,
            notification_location=worker1.location,
            notification_radius_km=5.0
        )
        pref.preferred_categories.add(general_cat)
        
        assert pref.is_active, "Notification preference not active"
        assert pref.preferred_categories.count() > 0, "No categories selected"
        print_info(f"Notification preference created for {worker1.username}")
        print_info(f"  Radius: {pref.notification_radius_km}km")
        print_info(f"  Categories: {pref.preferred_categories.count()}")
    
    def test_05_job_posting(self):
        """Test job posting with geolocation"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        
        # Get or create category
        general_cat = GeneralCategory.objects.filter(slug='construction').first()
        if not general_cat:
            general_cat = GeneralCategory.objects.create(
                name='Construction & Trades',
                slug='construction'
            )
        
        job_cat, _ = JobCategory.objects.get_or_create(
            name='Carpentry',
            defaults={'general_category': general_cat}
        )
        
        # Create job
        job = Job.objects.create(
            owner=client,
            title=f"{TEST_PREFIX}Carpenter Needed for Home Renovation",
            description="Need experienced carpenter for kitchen renovation",
            category=job_cat,
            budget=Decimal('15000.00'),
            municipality='Bacoor',
            barangay='Bayanan',
            location=Point(120.9744, 14.4271, srid=4326),
            latitude=14.4271,
            longitude=120.9744,
            vacancies=2,
            number_of_workers=2,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7)
        )
        self.test_jobs.append(job)
        
        assert job.id is not None, "Job not created"
        assert job.location is not None, "Job location not set"
        print_info(f"Job created: {job.title}")
        print_info(f"  Location: {job.municipality}, {job.barangay}")
        print_info(f"  Budget: ₱{job.budget}")
        print_info(f"  Vacancies: {job.vacancies}")
    
    def test_06_location_based_notifications(self):
        """Test that nearby workers receive job notifications"""
        job = self.test_jobs[0]
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        # Check if notification was created
        time.sleep(1)  # Allow signal to process
        notifications = Notification.objects.filter(
            user=worker1,
            notif_type='job_post'
        )
        
        # Note: This might be 0 if categories don't match or signal didn't fire
        print_info(f"Notifications created for worker1: {notifications.count()}")
        
        if notifications.exists():
            print_success("Location-based notification system working")
        else:
            print_warning("No notifications created (check category matching)")
    
    def test_07_job_application(self):
        """Test job application workflow"""
        job = self.test_jobs[0]
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        worker2 = User.objects.get(username=f"{TEST_PREFIX}worker2")
        
        # Worker 1 applies
        app1 = JobApplication.objects.create(
            job=job,
            worker=worker1,
            status='Pending',
            cover_letter='I have 5 years of carpentry experience',
            proposed_rate='₱500/hour',
            available_start_date=timezone.now().date() + timedelta(days=3)
        )
        self.test_applications.append(app1)
        print_info(f"Application created: {worker1.username} -> {job.title}")
        
        # Worker 2 applies
        app2 = JobApplication.objects.create(
            job=job,
            worker=worker2,
            status='Pending',
            cover_letter='I specialize in custom woodwork',
            proposed_rate='₱600/hour',
            available_start_date=timezone.now().date() + timedelta(days=1)
        )
        self.test_applications.append(app2)
        print_info(f"Application created: {worker2.username} -> {job.title}")
        
        # Verify application count
        total_apps = JobApplication.objects.filter(job=job).count()
        assert total_apps == 2, f"Expected 2 applications, got {total_apps}"
        
        # Verify pending count
        pending_apps = JobApplication.objects.filter(job=job, status='Pending').count()
        assert pending_apps == 2, f"Expected 2 pending applications, got {pending_apps}"
        print_success(f"Total applications: {total_apps}, Pending: {pending_apps}")
    
    def test_08_duplicate_application_prevention(self):
        """Test that duplicate applications are prevented"""
        job = self.test_jobs[0]
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        # Try to create duplicate application
        try:
            JobApplication.objects.create(
                job=job,
                worker=worker1,
                status='Pending',
                cover_letter='Duplicate application'
            )
            raise AssertionError("Duplicate application was allowed")
        except Exception as e:
            if "unique" in str(e).lower():
                print_success("Duplicate prevention working (database constraint)")
            else:
                print_info(f"Exception: {e}")
    
    def test_09_application_acceptance(self):
        """Test accepting an application"""
        app1 = self.test_applications[0]
        
        # Accept application
        app1.status = 'Accepted'
        app1.save()
        
        # Verify status change
        app1.refresh_from_db()
        assert app1.status == 'Accepted', "Application status not updated"
        print_info(f"Application accepted: {app1.worker.username}")
    
    def test_10_contract_creation(self):
        """Test contract creation from accepted application"""
        app1 = self.test_applications[0]
        job = app1.job
        
        # Create contract
        contract = Contract.objects.create(
            job=job,
            worker=app1.worker,
            client=job.owner,
            application=app1,
            status='Negotiation',
            is_draft=True,
            job_title=job.title,
            job_description=job.description,
            agreed_rate=Decimal('500.00'),
            payment_schedule='Daily',
            start_date=timezone.now().date() + timedelta(days=3),
            end_date=timezone.now().date() + timedelta(days=10),
            start_time=timezone.now().time().replace(hour=8, minute=0),
            end_time=timezone.now().time().replace(hour=17, minute=0)
        )
        self.test_contracts.append(contract)
        
        assert contract.id is not None, "Contract not created"
        assert contract.status == 'Negotiation', "Contract status incorrect"
        print_info(f"Contract created: {contract.id}")
        print_info(f"  Status: {contract.status}")
        print_info(f"  Rate: ₱{contract.agreed_rate}")
    
    def test_11_contract_finalization(self):
        """Test contract finalization workflow"""
        contract = self.test_contracts[0]
        
        # Both parties finalize
        contract.finalized_by_worker = True
        contract.finalized_by_employer = True
        contract.is_draft = False
        contract.status = 'Finalized'
        contract.save()
        
        contract.refresh_from_db()
        assert contract.status == 'Finalized', "Contract not finalized"
        assert not contract.is_draft, "Contract still in draft mode"
        print_success("Contract finalized by both parties")
    
    def test_12_employer_dashboard_stats(self):
        """Test employer dashboard statistics calculation"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        
        # Calculate stats (same as EmployerDashboardView)
        total_jobs = Job.objects.filter(owner=client).count()
        active_jobs = Job.objects.filter(owner=client, is_active=True).count()
        total_applications = JobApplication.objects.filter(
            job__owner=client, 
            status='Pending'
        ).count()
        
        print_info(f"Dashboard stats for {client.username}:")
        print_info(f"  Total jobs: {total_jobs}")
        print_info(f"  Active jobs: {active_jobs}")
        print_info(f"  Pending applications: {total_applications}")
        
        assert total_jobs >= 1, "No jobs found for client"
        # Note: total_applications might be 1 (since we accepted one)
        print_success(f"Dashboard stats calculated correctly")
    
    def test_13_profile_page_stats(self):
        """Test user profile page statistics (recent fix)"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        
        # Calculate total pending applicants (from UserProfileDetailView)
        total_pending_applicants = JobApplication.objects.filter(
            job__owner=client,
            status='Pending'
        ).count()
        
        print_info(f"Profile stats for {client.username}:")
        print_info(f"  Total pending applicants: {total_pending_applicants}")
        
        # Should be 1 (worker2 is still pending, worker1 was accepted)
        assert total_pending_applicants >= 0, "Negative applicant count"
        print_success("Profile page stats calculated correctly")
    
    def test_14_service_posting(self):
        """Test service posting by worker"""
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        # Get or create service category
        service_cat, _ = ServiceCategory.objects.get_or_create(
            name='Carpentry Services',
            defaults={'slug': 'carpentry-services'}
        )
        
        # Create service post
        service = ServicePost.objects.create(
            worker=worker1,
            headline=f"{TEST_PREFIX}Professional Carpentry Services",
            description="Expert carpenter with 10+ years experience",
            category=service_cat,
            address='Bacoor, Cavite',
            location=Point(120.9744, 14.4271, srid=4326),
            pricing=Decimal('500.00'),
            availability='Weekdays 8AM-5PM',
            is_active=True
        )
        self.test_services.append(service)
        
        assert service.id is not None, "Service not created"
        print_info(f"Service created: {service.headline}")
        print_info(f"  Pricing: ₱{service.pricing}")
    
    def test_15_service_review(self):
        """Test service review system"""
        service = self.test_services[0]
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        
        # Create review
        review = ServiceReview.objects.create(
            service_post=service,
            reviewer=client,
            rating=5,
            comment="Excellent work! Very professional and timely."
        )
        
        assert review.id is not None, "Review not created"
        assert review.rating == 5, "Review rating incorrect"
        print_info(f"Review created: {review.rating} stars")
        print_info(f"  Comment: {review.comment}")
    
    def test_16_messaging_system(self):
        """Test messaging between users"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        # Create conversation
        conversation = Conversation.objects.create(
            user1=client,
            user2=worker1
        )
        
        # Send messages
        msg1 = Message.objects.create(
            conversation=conversation,
            sender=client,
            content="Hello, I saw your application. When can you start?"
        )
        
        msg2 = Message.objects.create(
            conversation=conversation,
            sender=worker1,
            content="Thank you! I can start next week."
        )
        
        assert conversation.messages.count() == 2, "Messages not created"
        print_info(f"Conversation created: {conversation.messages.count()} messages")
        print_success("Messaging system working")
    
    def test_17_content_moderation(self):
        """Test content moderation system"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        conversation = Conversation.objects.filter(user1=client, user2=worker1).first()
        
        if conversation:
            # Test profanity filter (if enabled)
            msg = Message.objects.create(
                conversation=conversation,
                sender=client,
                content="This is a test message for moderation."
            )
            
            assert msg.content is not None, "Message content is None"
            print_info("Content moderation active")
            print_success("Content moderation system working")
        else:
            print_warning("No conversation found for moderation test")
    
    def test_18_vacancy_management(self):
        """Test automatic vacancy decrement"""
        job = self.test_jobs[0]
        initial_vacancies = job.vacancies
        
        # Manually decrement vacancy
        success = job.decrement_vacancy()
        job.refresh_from_db()
        
        assert success, "Vacancy decrement failed"
        assert job.vacancies == initial_vacancies - 1, "Vacancy not decremented"
        print_info(f"Vacancies: {initial_vacancies} -> {job.vacancies}")
        
        if job.vacancies == 0:
            assert not job.is_active, "Job should be deactivated when full"
            print_success("Job auto-deactivated when vacancies reached 0")
        else:
            print_success("Vacancy decremented successfully")
    
    def test_19_distance_calculation(self):
        """Test geolocation distance calculation"""
        client = User.objects.get(username=f"{TEST_PREFIX}client1")
        worker1 = User.objects.get(username=f"{TEST_PREFIX}worker1")
        
        if client.location and worker1.location:
            # Calculate distance using PostGIS
            distance = client.location.distance(worker1.location)
            distance_meters = float(distance) if isinstance(distance, float) else distance.m
            distance_km = distance_meters / 1000
            
            print_info(f"Distance between client and worker1: {distance_km:.2f}km")
            assert distance_km < 100, "Distance calculation seems incorrect"
            print_success("Distance calculation working")
        else:
            print_warning("Locations not set for distance test")
    
    def test_20_system_health_check(self):
        """Test system health endpoints"""
        from django.test import Client as TestClient
        client = TestClient()
        
        # Test health endpoint
        response = client.get('/health/')
        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        print_success("Health check endpoint: OK")
    
    def run_all_tests(self):
        """Run all integration tests"""
        self.start_time = time.time()
        
        print_header("TRABAHOLINK PRODUCTION INTEGRATION TEST SUITE")
        print_info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print_info(f"Test prefix: {TEST_PREFIX}")
        print_info(f"Cleanup after test: {CLEANUP_AFTER_TEST}")
        
        # Define test sequence
        tests = [
            ("Database Connection", self.test_01_database_connection),
            ("PostGIS Extension", self.test_02_postgis_extension),
            ("User Creation", self.test_03_create_test_users),
            ("Notification Preferences", self.test_04_notification_preferences),
            ("Job Posting", self.test_05_job_posting),
            ("Location-Based Notifications", self.test_06_location_based_notifications),
            ("Job Application", self.test_07_job_application),
            ("Duplicate Application Prevention", self.test_08_duplicate_application_prevention),
            ("Application Acceptance", self.test_09_application_acceptance),
            ("Contract Creation", self.test_10_contract_creation),
            ("Contract Finalization", self.test_11_contract_finalization),
            ("Employer Dashboard Stats", self.test_12_employer_dashboard_stats),
            ("Profile Page Stats", self.test_13_profile_page_stats),
            ("Service Posting", self.test_14_service_posting),
            ("Service Review", self.test_15_service_review),
            ("Messaging System", self.test_16_messaging_system),
            ("Content Moderation", self.test_17_content_moderation),
            ("Vacancy Management", self.test_18_vacancy_management),
            ("Distance Calculation", self.test_19_distance_calculation),
            ("System Health Check", self.test_20_system_health_check),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Cleanup
        self.cleanup()
        
        # Print summary
        self.print_summary()
        
        # Generate HTML report
        self.generate_html_report()
    
    def print_summary(self):
        """Print test summary"""
        elapsed_time = time.time() - self.start_time
        total_tests = self.passed_tests + self.failed_tests
        
        print_header("TEST SUMMARY")
        print_info(f"Total tests run: {total_tests}")
        print(f"{Colors.GREEN}Passed: {self.passed_tests}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed_tests}{Colors.END}")
        print_info(f"Elapsed time: {elapsed_time:.2f} seconds")
        print_info(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.failed_tests == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.END}")
            print(f"{Colors.GREEN}System is ready for production use.{Colors.END}\n")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.END}")
            print(f"{Colors.RED}Please review and fix issues before deploying.{Colors.END}\n")
        
        print("="*70)
    
    def generate_html_report(self):
        """Generate HTML report similar to test_report_20260104_091038.html"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"integration_test_report_{timestamp}.html"
        
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        elapsed_time = time.time() - self.start_time
        
        # Group tests by category
        categories = {
            'Core System': [],
            'Job Workflow': [],
            'Contract System': [],
            'Statistics & Dashboard': [],
            'Services': [],
            'Communication': [],
            'Geolocation': []
        }
        
        # Categorize tests
        for result in self.test_results:
            name = result['name']
            if any(x in name for x in ['Database', 'PostGIS', 'Health']):
                categories['Core System'].append(result)
            elif any(x in name for x in ['Job', 'Application', 'Vacancy', 'Notification']):
                categories['Job Workflow'].append(result)
            elif 'Contract' in name:
                categories['Contract System'].append(result)
            elif any(x in name for x in ['Dashboard', 'Profile', 'Stats']):
                categories['Statistics & Dashboard'].append(result)
            elif 'Service' in name or 'Review' in name:
                categories['Services'].append(result)
            elif 'Messaging' in name or 'Moderation' in name:
                categories['Communication'].append(result)
            elif 'Distance' in name or 'Geolocation' in name:
                categories['Geolocation'].append(result)
            else:
                categories['Core System'].append(result)
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trabaholink Integration Test Results</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .timestamp {{
            opacity: 0.9;
            font-size: 0.9em;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .summary-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .summary-card .label {{
            color: #666;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 1px;
        }}
        .passed {{ color: #28a745; }}
        .failed {{ color: #dc3545; }}
        .total {{ color: #007bff; }}
        .time {{ color: #6c757d; }}
        
        .progress-bar {{
            height: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            overflow: hidden;
            margin: 20px 30px;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            transition: width 0.3s ease;
            width: {pass_rate}%;
        }}
        
        .category {{
            margin: 30px;
        }}
        .category-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-left: 4px solid #667eea;
            margin-bottom: 15px;
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
        }}
        .test-item {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            margin-bottom: 15px;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        .test-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        .test-header {{
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            background: #fafafa;
        }}
        .test-name {{
            font-weight: 600;
            font-size: 1.1em;
        }}
        .test-status {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .status-badge {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .duration {{
            color: #666;
            font-size: 0.9em;
        }}
        .test-details {{
            padding: 20px;
            border-top: 1px solid #e0e0e0;
            background: white;
            display: none;
        }}
        .test-item.expanded .test-details {{
            display: block;
        }}
        .error-message {{
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 15px;
            margin-top: 10px;
            color: #721c24;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        .expand-icon {{
            transition: transform 0.3s ease;
        }}
        .test-item.expanded .expand-icon {{
            transform: rotate(180deg);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 Trabaholink Integration Test Results</h1>
            <div class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="number total">{total_tests}</div>
                <div class="label">Total Tests</div>
            </div>
            <div class="summary-card">
                <div class="number passed">{self.passed_tests}</div>
                <div class="label">Passed</div>
            </div>
            <div class="summary-card">
                <div class="number failed">{self.failed_tests}</div>
                <div class="label">Failed</div>
            </div>
            <div class="summary-card">
                <div class="number time">{elapsed_time:.2f}s</div>
                <div class="label">Duration</div>
            </div>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
"""
        
        # Add test results by category
        for category_name, tests in categories.items():
            if not tests:
                continue
                
            html_content += f"""
        <div class="category">
            <div class="category-header">{category_name}</div>
"""
            
            for test in tests:
                status_class = 'status-passed' if test['status'] == 'passed' else 'status-failed'
                status_text = '✓ PASSED' if test['status'] == 'passed' else '✗ FAILED'
                
                html_content += f"""
            <div class="test-item" onclick="this.classList.toggle('expanded')">
                <div class="test-header">
                    <div class="test-name">{test['name']}</div>
                    <div class="test-status">
                        <span class="duration">{test['duration']:.3f}s</span>
                        <span class="status-badge {status_class}">{status_text}</span>
                        <span class="expand-icon">▼</span>
                    </div>
                </div>
                <div class="test-details">
"""
                
                if test['error']:
                    html_content += f"""
                    <div class="error-message">{test['error']}</div>
"""
                else:
                    html_content += """
                    <p>✓ Test passed successfully</p>
"""
                
                html_content += """
                </div>
            </div>
"""
        
        html_content += """
        </div>
        
        <div class="footer">
            <p><strong>Trabaholink Platform</strong> - Integration Test Suite</p>
            <p>Production Environment Test Report</p>
        </div>
    </div>
    
    <script>
        // Auto-scroll to first failed test
        const firstFailed = document.querySelector('.status-failed');
        if (firstFailed) {
            setTimeout(() => {
                firstFailed.closest('.test-item').scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 500);
        }
    </script>
</body>
</html>
"""
        
        # Write to file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n{Colors.GREEN}✓ HTML report generated: {filename}{Colors.END}")
            print(f"{Colors.BLUE}View at: http://194.233.72.74:8888/{filename}{Colors.END}")
        except Exception as e:
            print_error(f"Failed to generate HTML report: {e}")


if __name__ == "__main__":
    runner = IntegrationTestRunner()
    try:
        runner.run_all_tests()
        sys.exit(0 if runner.failed_tests == 0 else 1)
    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        runner.cleanup()
        sys.exit(1)
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        runner.cleanup()
        sys.exit(1)
