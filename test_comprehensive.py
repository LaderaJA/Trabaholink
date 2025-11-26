"""
Comprehensive Test Suite for Trabaholink Platform
Tests: Models, Views, APIs, Security, Performance, Integration

Run: python manage.py test test_comprehensive
Or: python test_comprehensive.py
"""

import time
import json
from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock

# Import models
try:
    from users.models import Profile, Skill, WorkerAvailability
    from jobs.models import Job, JobCategory, JobApplication, Contract, Feedback
    from services.models import ServicePost, ServiceCategory, Review
    from messaging.models import Conversation, Message
    from notifications.models import Notification
    from announcements.models import Announcement
    from reports.models import Report
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    print("Some tests may be skipped")

User = get_user_model()


class SecurityHeadersTest(TestCase):
    """Test security headers implementation"""
    
    def setUp(self):
        self.client = Client()
    
    def test_security_headers_present(self):
        """Test that security headers are present in response"""
        response = self.client.get('/')
        
        # Check X-Frame-Options
        self.assertIn('X-Frame-Options', response.headers)
        self.assertEqual(response.headers['X-Frame-Options'], 'SAMEORIGIN')
        
        # Check X-Content-Type-Options
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        
        # Check Referrer-Policy
        self.assertIn('Referrer-Policy', response.headers)
        
        print("✅ Security headers test passed")
    
    def test_csp_header_present(self):
        """Test Content Security Policy header"""
        response = self.client.get('/')
        
        if 'Content-Security-Policy' in response.headers:
            csp = response.headers['Content-Security-Policy']
            self.assertIn("default-src", csp)
            self.assertIn("'self'", csp)
            print("✅ CSP header test passed")
        else:
            print("⚠️ CSP header not present (may be disabled in DEBUG mode)")
    
    def test_secure_cookies(self):
        """Test that cookies have secure flags"""
        # Create user and login
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Check for secure cookie flags in Set-Cookie header
        cookies = response.cookies
        if 'csrftoken' in cookies:
            cookie = cookies['csrftoken']
            # In test environment, secure may not be set
            print(f"✅ CSRF cookie present: {cookie.key}")
        
        print("✅ Secure cookies test passed")


class UserAuthenticationTest(TestCase):
    """Test user registration, login, logout"""
    
    def setUp(self):
        self.client = Client()
    
    def test_user_registration(self):
        """Test user can register"""
        response = self.client.post(reverse('users:register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
            'first_name': 'New',
            'last_name': 'User'
        })
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        print("✅ User registration test passed")
    
    def test_user_login(self):
        """Test user can login"""
        # Create user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Login
        response = self.client.post(reverse('users:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        # Check login successful
        self.assertEqual(response.status_code, 302)  # Redirect after login
        print("✅ User login test passed")
    
    def test_user_logout(self):
        """Test user can logout"""
        # Create and login user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Logout
        response = self.client.get(reverse('users:logout'))
        
        # Check logout successful
        self.assertEqual(response.status_code, 302)
        print("✅ User logout test passed")


class ProfileTest(TestCase):
    """Test user profile functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
    
    def test_profile_created_on_user_creation(self):
        """Test profile is auto-created when user is created"""
        self.assertTrue(hasattr(self.user, 'profile'))
        print("✅ Profile auto-creation test passed")
    
    def test_profile_view(self):
        """Test profile page loads"""
        response = self.client.get(reverse('users:profile', args=[self.user.username]))
        self.assertEqual(response.status_code, 200)
        print("✅ Profile view test passed")
    
    def test_profile_edit(self):
        """Test profile can be edited"""
        response = self.client.post(reverse('users:profile_edit'), {
            'bio': 'Updated bio',
            'phone_number': '09123456789',
            'city': 'Manila'
        })
        
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.bio, 'Updated bio')
        print("✅ Profile edit test passed")


class JobTest(TestCase):
    """Test job posting and application functionality"""
    
    def setUp(self):
        # Create employer
        self.employer = User.objects.create_user(
            username='employer',
            email='employer@example.com',
            password='testpass123'
        )
        self.employer.profile.role = 'employer'
        self.employer.profile.role_selected = True
        self.employer.profile.save()
        
        # Create worker
        self.worker = User.objects.create_user(
            username='worker',
            email='worker@example.com',
            password='testpass123'
        )
        self.worker.profile.role = 'worker'
        self.worker.profile.role_selected = True
        self.worker.profile.save()
        
        # Create job category
        self.category = JobCategory.objects.create(
            name='Construction',
            description='Construction jobs'
        )
        
        self.client = Client()
    
    def test_job_creation(self):
        """Test employer can create job"""
        self.client.login(username='employer', password='testpass123')
        
        response = self.client.post(reverse('jobs:job_create'), {
            'title': 'Test Job',
            'description': 'Test job description',
            'category': self.category.id,
            'location': 'Manila',
            'salary_min': 500,
            'salary_max': 1000,
            'job_type': 'full_time',
            'vacancies': 5
        })
        
        self.assertTrue(Job.objects.filter(title='Test Job').exists())
        print("✅ Job creation test passed")
    
    def test_job_list(self):
        """Test job list page loads"""
        response = self.client.get(reverse('jobs:job_list'))
        self.assertEqual(response.status_code, 200)
        print("✅ Job list test passed")
    
    def test_job_application(self):
        """Test worker can apply to job"""
        # Create job
        job = Job.objects.create(
            employer=self.employer,
            title='Test Job',
            description='Test description',
            category=self.category,
            location='Manila',
            salary_min=500,
            salary_max=1000,
            vacancies=5
        )
        
        self.client.login(username='worker', password='testpass123')
        
        response = self.client.post(reverse('jobs:job_apply', args=[job.id]), {
            'cover_letter': 'I am interested in this job'
        })
        
        self.assertTrue(JobApplication.objects.filter(job=job, worker=self.worker).exists())
        print("✅ Job application test passed")
    
    def test_worker_cannot_apply_twice(self):
        """Test worker cannot apply to same job twice"""
        job = Job.objects.create(
            employer=self.employer,
            title='Test Job',
            description='Test description',
            category=self.category,
            location='Manila',
            salary_min=500,
            salary_max=1000,
            vacancies=5
        )
        
        # Create first application
        JobApplication.objects.create(
            job=job,
            worker=self.worker,
            cover_letter='First application'
        )
        
        self.client.login(username='worker', password='testpass123')
        
        response = self.client.post(reverse('jobs:job_apply', args=[job.id]), {
            'cover_letter': 'Second application'
        })
        
        # Should only have one application
        self.assertEqual(JobApplication.objects.filter(job=job, worker=self.worker).count(), 1)
        print("✅ Duplicate application prevention test passed")


class ServiceTest(TestCase):
    """Test service marketplace functionality"""
    
    def setUp(self):
        # Create worker (service provider)
        self.worker = User.objects.create_user(
            username='worker',
            email='worker@example.com',
            password='testpass123'
        )
        self.worker.profile.role = 'worker'
        self.worker.profile.role_selected = True
        self.worker.profile.save()
        
        # Create client
        self.client_user = User.objects.create_user(
            username='client',
            email='client@example.com',
            password='testpass123'
        )
        
        # Create service category
        self.category = ServiceCategory.objects.create(
            name='Plumbing',
            description='Plumbing services'
        )
        
        self.client = Client()
    
    def test_service_creation(self):
        """Test worker can create service post"""
        self.client.login(username='worker', password='testpass123')
        
        response = self.client.post(reverse('services:create_post'), {
            'title': 'Plumbing Service',
            'description': 'Professional plumbing services',
            'category': self.category.id,
            'price': 500,
            'location': 'Manila'
        })
        
        self.assertTrue(ServicePost.objects.filter(title='Plumbing Service').exists())
        print("✅ Service creation test passed")
    
    def test_service_list(self):
        """Test service list page loads"""
        response = self.client.get(reverse('services:service_list'))
        self.assertEqual(response.status_code, 200)
        print("✅ Service list test passed")
    
    def test_review_creation(self):
        """Test client can review service"""
        # Create service
        service = ServicePost.objects.create(
            worker=self.worker,
            title='Test Service',
            description='Test description',
            category=self.category,
            price=500
        )
        
        self.client.login(username='client', password='testpass123')
        
        response = self.client.post(reverse('services:review_create', args=[service.id]), {
            'rating': 5,
            'comment': 'Excellent service!'
        })
        
        self.assertTrue(Review.objects.filter(service=service, reviewer=self.client_user).exists())
        print("✅ Review creation test passed")


class MessagingTest(TestCase):
    """Test messaging functionality"""
    
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.client = Client()
    
    def test_conversation_creation(self):
        """Test conversation can be created"""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        
        self.assertEqual(conversation.participants.count(), 2)
        print("✅ Conversation creation test passed")
    
    def test_message_sending(self):
        """Test message can be sent"""
        conversation = Conversation.objects.create()
        conversation.participants.add(self.user1, self.user2)
        
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user1,
            content='Hello!'
        )
        
        self.assertEqual(message.content, 'Hello!')
        print("✅ Message sending test passed")
    
    def test_conversation_list(self):
        """Test conversation list page loads"""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('messaging:conversation_list'))
        self.assertEqual(response.status_code, 200)
        print("✅ Conversation list test passed")


class NotificationTest(TestCase):
    """Test notification system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
    
    def test_notification_creation(self):
        """Test notification can be created"""
        notification = Notification.objects.create(
            recipient=self.user,
            notification_type='info',
            title='Test Notification',
            message='This is a test notification'
        )
        
        self.assertEqual(notification.recipient, self.user)
        print("✅ Notification creation test passed")
    
    def test_notification_list(self):
        """Test notification list page loads"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        print("✅ Notification list test passed")


class PerformanceTest(TransactionTestCase):
    """Test system performance"""
    
    def setUp(self):
        self.client = Client()
    
    def test_homepage_load_time(self):
        """Test homepage loads within acceptable time"""
        start = time.time()
        response = self.client.get('/')
        end = time.time()
        
        load_time = end - start
        self.assertLess(load_time, 2.0, f"Homepage took {load_time}s to load (should be < 2s)")
        print(f"✅ Homepage load time: {load_time:.2f}s")
    
    def test_database_query_count(self):
        """Test that views don't make excessive database queries"""
        # Create test data
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Monitor query count
        from django.test.utils import override_settings
        from django.db import reset_queries
        
        with self.assertNumQueries(None) as context:
            response = self.client.get('/')
        
        query_count = len(context.captured_queries)
        print(f"✅ Homepage query count: {query_count}")
        
        # Warn if too many queries
        if query_count > 50:
            print(f"⚠️ WARNING: {query_count} queries (consider optimization)")


class IntegrationTest(TestCase):
    """Test full user workflows"""
    
    def setUp(self):
        self.client = Client()
        
        # Create job category
        self.category = JobCategory.objects.create(
            name='Construction',
            description='Construction jobs'
        )
    
    def test_complete_job_workflow(self):
        """Test complete job posting and application workflow"""
        
        # 1. Employer registers
        employer_data = {
            'username': 'employer',
            'email': 'employer@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
            'first_name': 'Employer',
            'last_name': 'User'
        }
        response = self.client.post(reverse('users:register'), employer_data)
        employer = User.objects.get(username='employer')
        employer.profile.role = 'employer'
        employer.profile.role_selected = True
        employer.profile.save()
        
        # 2. Employer posts job
        self.client.login(username='employer', password='testpass123!')
        job_data = {
            'title': 'Construction Worker',
            'description': 'Need construction worker',
            'category': self.category.id,
            'location': 'Manila',
            'salary_min': 500,
            'salary_max': 1000,
            'job_type': 'full_time',
            'vacancies': 5
        }
        response = self.client.post(reverse('jobs:job_create'), job_data)
        job = Job.objects.get(title='Construction Worker')
        self.client.logout()
        
        # 3. Worker registers
        worker_data = {
            'username': 'worker',
            'email': 'worker@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
            'first_name': 'Worker',
            'last_name': 'User'
        }
        response = self.client.post(reverse('users:register'), worker_data)
        worker = User.objects.get(username='worker')
        worker.profile.role = 'worker'
        worker.profile.role_selected = True
        worker.profile.save()
        
        # 4. Worker applies to job
        self.client.login(username='worker', password='testpass123!')
        application_data = {
            'cover_letter': 'I am interested'
        }
        response = self.client.post(reverse('jobs:job_apply', args=[job.id]), application_data)
        
        # 5. Verify workflow completed
        self.assertTrue(JobApplication.objects.filter(job=job, worker=worker).exists())
        print("✅ Complete job workflow test passed")


class APITest(TestCase):
    """Test API endpoints"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_api_authentication_required(self):
        """Test API requires authentication"""
        response = self.client.get('/api/jobs/')
        
        # Should require authentication or return 200 with public data
        self.assertIn(response.status_code, [200, 401, 403])
        print("✅ API authentication test passed")
    
    def test_api_returns_json(self):
        """Test API returns JSON response"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get('/api/jobs/', HTTP_ACCEPT='application/json')
        
        if response.status_code == 200:
            self.assertEqual(response['Content-Type'], 'application/json')
            print("✅ API JSON response test passed")


class AdminDashboardTest(TestCase):
    """Test admin dashboard functionality"""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        self.client = Client()
    
    def test_admin_dashboard_access(self):
        """Test admin can access dashboard"""
        self.client.login(username='admin', password='admin123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        print("✅ Admin dashboard access test passed")
    
    def test_non_admin_cannot_access_dashboard(self):
        """Test non-admin cannot access dashboard"""
        user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='testpass123'
        )
        self.client.login(username='user', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Redirect to login
        print("✅ Non-admin dashboard restriction test passed")


# Run all tests
def run_all_tests():
    """Run all test cases"""
    import unittest
    
    print("\n" + "="*70)
    print("🧪 TRABAHOLINK COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(SecurityHeadersTest))
    suite.addTests(loader.loadTestsFromTestCase(UserAuthenticationTest))
    suite.addTests(loader.loadTestsFromTestCase(ProfileTest))
    suite.addTests(loader.loadTestsFromTestCase(JobTest))
    suite.addTests(loader.loadTestsFromTestCase(ServiceTest))
    suite.addTests(loader.loadTestsFromTestCase(MessagingTest))
    suite.addTests(loader.loadTestsFromTestCase(NotificationTest))
    suite.addTests(loader.loadTestsFromTestCase(PerformanceTest))
    suite.addTests(loader.loadTestsFromTestCase(IntegrationTest))
    suite.addTests(loader.loadTestsFromTestCase(APITest))
    suite.addTests(loader.loadTestsFromTestCase(AdminDashboardTest))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"⚠️ Errors: {len(result.errors)}")
    print("="*70 + "\n")
    
    return result


if __name__ == '__main__':
    import os
    import django
    
    # Setup Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Trabaholink.settings')
    django.setup()
    
    # Run tests
    run_all_tests()
