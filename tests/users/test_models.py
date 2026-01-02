"""
Unit tests for users app models
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from faker import Faker

User = get_user_model()
fake = Faker()

pytestmark = pytest.mark.django_db


class TestUserModel:
    """Test CustomUser model"""
    
    def test_create_user(self):
        """Test creating a regular user"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.check_password('TestPass123!')
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
    
    def test_create_superuser(self):
        """Test creating a superuser"""
        import uuid
        admin = User.objects.create_superuser(
            username=f'admin_{uuid.uuid4().hex[:8]}',
            email=f'admin_{uuid.uuid4().hex[:8]}@example.com',
            password='AdminPass123!'
        )
        assert admin.is_staff
        assert admin.is_superuser
        assert admin.is_active
    
    def test_user_string_representation(self, create_user):
        """Test user __str__ method"""
        assert str(create_user) == create_user.username
    
    def test_user_email_unique(self):
        """Test that email field allows duplicates (not enforced as unique in model)"""
        import uuid
        email = f'unique_{uuid.uuid4().hex[:8]}@example.com'
        user1 = User.objects.create_user(
            username=f'user1_{uuid.uuid4().hex[:8]}',
            email=email,
            password='TestPass123!'
        )
        # Email uniqueness is not enforced at database level
        # Users can have the same email (business logic may prevent this at form level)
        user2 = User.objects.create_user(
            username=f'user2_{uuid.uuid4().hex[:8]}',
            email=email,  # Same email is allowed
            password='TestPass123!'
        )
        assert user1.email == user2.email
    
    def test_user_username_unique(self, create_user):
        """Test that username must be unique"""
        with pytest.raises(Exception):
            User.objects.create_user(
                username=create_user.username,
                email='different@example.com',
                password='TestPass123!'
            )
    
    def test_user_role_choices(self):
        """Test user role field choices"""
        worker = User.objects.create_user(
            username='worker',
            email='worker@example.com',
            password='TestPass123!',
            role='worker'
        )
        assert worker.role == 'worker'
        
        employer = User.objects.create_user(
            username='employer',
            email='employer@example.com',
            password='TestPass123!',
            role='employer'
        )
        assert employer.role == 'employer'
    
    def test_user_profile_fields(self, create_user):
        """Test user profile fields"""
        create_user.bio = 'Test bio'
        create_user.address = 'Test address'
        create_user.contact_number = '+1234567890'
        create_user.save()
        
        user = User.objects.get(pk=create_user.pk)
        assert user.bio == 'Test bio'
        assert user.address == 'Test address'
        assert user.contact_number == '+1234567890'
    
    def test_user_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='John',
            last_name='Doe'
        )
        assert user.get_full_name() == 'John Doe'
    
    def test_user_verification_status(self, create_user):
        """Test user verification field"""
        assert not create_user.is_verified
        create_user.is_verified = True
        create_user.save()
        assert create_user.is_verified
