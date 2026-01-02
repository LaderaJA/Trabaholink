"""
Pytest configuration and fixtures for TrabahoLink tests
"""
import pytest
from django.contrib.auth import get_user_model
from faker import Faker

User = get_user_model()
fake = Faker()


@pytest.fixture
def user_data():
    """Generate fake user data"""
    return {
        'username': fake.user_name(),
        'email': fake.email(),
        'password': 'TestPassword123!',
        'first_name': fake.first_name(),
        'last_name': fake.last_name(),
    }


@pytest.fixture
def create_user(db, user_data):
    """Create a test user"""
    return User.objects.create_user(**user_data)


@pytest.fixture
def create_worker(db):
    """Create a worker user"""
    import uuid
    return User.objects.create_user(
        username=f'worker_{uuid.uuid4().hex[:8]}',
        email=f'worker_{uuid.uuid4().hex[:8]}@example.com',
        password='TestPassword123!',
        role='worker'
    )


@pytest.fixture
def create_employer(db):
    """Create an employer user"""
    import uuid
    return User.objects.create_user(
        username=f'employer_{uuid.uuid4().hex[:8]}',
        email=f'employer_{uuid.uuid4().hex[:8]}@example.com',
        password='TestPassword123!',
        role='client'  # Actual role in your model
    )


@pytest.fixture
def authenticated_client(client, create_user):
    """Return an authenticated client"""
    client.force_login(create_user)
    return client


@pytest.fixture
def worker_client(client, create_worker):
    """Return an authenticated worker client"""
    client.force_login(create_worker)
    return client


@pytest.fixture
def employer_client(client, create_employer):
    """Return an authenticated employer client"""
    client.force_login(create_employer)
    return client


@pytest.fixture(scope='session')
def django_db_setup():
    """Override database settings to use SQLite for tests"""
    from django.conf import settings
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': False,
        'AUTOCOMMIT': True,
        'CONN_MAX_AGE': 0,
    }


@pytest.fixture(autouse=True)
def disable_historical_models(settings):
    """Disable django-simple-history for tests to avoid modeltranslation conflicts"""
    settings.SIMPLE_HISTORY_ENABLED = False
    
    # Also disable modeltranslation field creation in tests
    settings.MODELTRANSLATION_PREPOPULATE = False
    settings.MODELTRANSLATION_AUTO_POPULATE = False


@pytest.fixture(autouse=True)
def setup_site(db, settings):
    """Create a default Site object for tests that require it"""
    from django.contrib.sites.models import Site
    
    # Set SITE_ID in settings
    settings.SITE_ID = 1
    
    # Create or get the site
    Site.objects.get_or_create(
        id=1,
        defaults={'domain': 'testserver', 'name': 'Test Site'}
    )


@pytest.fixture
def client_no_middleware(client):
    """Client with middleware bypassed for testing"""
    return client


@pytest.fixture
def create_user_with_role(db):
    """Create a user with role already selected"""
    import uuid
    user = User.objects.create_user(
        username=f'user_{uuid.uuid4().hex[:8]}',
        email=f'user_{uuid.uuid4().hex[:8]}@example.com',
        password='TestPassword123!',
        role='worker',
        has_selected_role=True  # Bypass role selection middleware
    )
    return user


@pytest.fixture
def client_bypass_middleware(client, create_user_with_role):
    """Authenticated client that bypasses middleware"""
    client.force_login(create_user_with_role)
    return client
