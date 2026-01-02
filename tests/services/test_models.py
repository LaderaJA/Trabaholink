"""Unit tests for services app models"""
import pytest
from django.contrib.auth import get_user_model
from services.models import ServiceCategory, ServicePost
from decimal import Decimal
import uuid

User = get_user_model()
pytestmark = pytest.mark.django_db


class TestServiceCategoryModel:
    def test_create_service_category(self):
        category = ServiceCategory.objects.create(name=f'Plumbing_{uuid.uuid4().hex[:8]}')
        assert 'Plumbing' in category.name
        assert str(category) == category.name


class TestServicePostModel:
    def test_create_service_post(self, create_worker):
        category = ServiceCategory.objects.create(name=f'Electrical_{uuid.uuid4().hex[:8]}')
        service = ServicePost.objects.create(
            worker=create_worker,
            category=category,
            headline='Professional Electrician',
            description='Expert electrical services',
            pricing=Decimal('500.00'),
            availability='Monday to Friday',
            contact_number='09123456789',
            email=f'electrician_{uuid.uuid4().hex[:8]}@example.com',
            address='Quezon City'
        )
        assert service.headline == 'Professional Electrician'
        assert service.worker == create_worker
        assert service.pricing == Decimal('500.00')
