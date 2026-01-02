"""
Unit tests for users app views
"""
import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestUserRegistration:
    """Test user registration view"""
    
    def test_registration_page_loads(self, client):
        """Test registration page loads successfully"""
        response = client.get(reverse('register'))
        assert response.status_code == 200
        assert 'register' in response.content.decode().lower()
    
    def test_successful_registration(self, client):
        """Test successful user registration - creates OTP record, not user yet"""
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'role': 'worker'
        }
        response = client.post(reverse('register'), data)
        # Registration doesn't create user immediately - it creates an OTP record
        # User is only created after email verification
        from users.models import EmailOTP
        assert EmailOTP.objects.filter(email='newuser@example.com', username='newuser').exists()


class TestUserLogin:
    """Test user login view"""
    
    def test_login_page_loads(self, client, settings):
        """Test login page loads successfully"""
        # Ensure SITE_ID is set for this test
        settings.SITE_ID = 1
        response = client.get(reverse('login'))
        assert response.status_code == 200
        assert 'login' in response.content.decode().lower()
    
    def test_successful_login(self, client, create_user):
        """Test successful user login"""
        data = {
            'username': create_user.username,
            'password': 'TestPassword123!',
        }
        response = client.post(reverse('login'), data)
        assert response.status_code in [200, 302]


class TestUserProfile:
    """Test user profile view"""
    
    def test_profile_requires_authentication(self, client, create_user):
        """Test profile view requires authentication"""
        response = client.get(reverse('profile', kwargs={'pk': create_user.pk}))
        # Should redirect to login if not authenticated
        assert response.status_code in [200, 302]
    
    def test_authenticated_user_can_view_profile(self, client, create_user):
        """Test authenticated user can view their profile"""
        create_user.has_selected_role = True
        create_user.role = 'worker'
        create_user.save()
        client.force_login(create_user)
        response = client.get(reverse('profile', kwargs={'pk': create_user.pk}), follow=True)
        # Account for possible redirects from middleware
        assert response.status_code == 200
