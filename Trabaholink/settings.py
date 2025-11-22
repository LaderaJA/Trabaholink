from pathlib import Path
import os

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-j%%kku167m+le-25a0+o-0qvl64osod4=tf!ab$*9h!y$^9viy')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.sites',
    "corsheaders",
    
    'rest_framework',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'channels',
    'django_celery_beat',
    'messaging',
    'users',
    'jobs',
    'reports',
    'announcements',
    'admin_dashboard',
    'notifications',
    'services',
    'posts',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'users.middleware.RoleSelectionMiddleware',  # ✅ Force role selection for new social users
    'notifications.middleware.NotificationMiddleware',
    'jobs.middleware.ExpiredJobsMiddleware',  # Auto-deactivate expired jobs
]

# Trust proxy headers (for ngrok and reverse proxies)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True


ROOT_URLCONF = 'Trabaholink.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/ 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'notifications.context_processors.unread_notifications',
                'admin_dashboard.context_processors.admin_notifications',
                'jobs.context_processors.user_dashboard_access',
            ],
        },
    },
]

WSGI_APPLICATION = 'Trabaholink.wsgi.application'

ASGI_APPLICATION = "Trabaholink.asgi.application"
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.environ.get('REDIS_HOST', '127.0.0.1'), int(os.environ.get('REDIS_PORT', 6379)))],  
        },
    },
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vue.js frontend
]


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.environ.get('DB_ENGINE', 'django.contrib.gis.db.backends.postgis'),
        'NAME': os.environ.get('DB_NAME', 'trabaholink_db'), 
        'USER': os.environ.get('DB_USER', 'trabaholink_db'), 
        'PASSWORD': os.environ.get('DB_PASSWORD', '121628'),  
        'HOST': os.environ.get('DB_HOST', 'localhost'), 
        'PORT': os.environ.get('DB_PORT', '5432'), 
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = "Asia/Manila"  # or your desired timezone
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR/'media'

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'  # New line added

AUTH_USER_MODEL = 'users.CustomUser'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Use Django's built-in authentication system
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]


# Redirect users after login/logout
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = 'jobs:home'  
LOGOUT_REDIRECT_URL = 'login'

EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'trabaholinka@gmail.com')

# SendGrid Configuration
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')

# SMTP Configuration (fallback)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# OTP Settings
OTP_EXPIRY_MINUTES = 10  # OTP expires after 10 minutes
OTP_LENGTH = 6  # 6-digit OTP code

GDAL_LIBRARY_PATH = os.getenv('GDAL_LIBRARY_PATH', '/usr/lib/libgdal.so')

# Django Allauth Configuration
SITE_ID = 1

# Allauth settings
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = 'none'  # We handle email verification with OTP
ACCOUNT_USERNAME_REQUIRED = True
SOCIALACCOUNT_AUTO_SIGNUP = True  # Auto-signup, then redirect to role selection
ACCOUNT_ADAPTER = 'users.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_LOGIN_ON_GET = True  # Allow social login via GET request
LOGIN_ERROR_URL = '/users/register/'  # Redirect on social login cancellation

# Allow connecting social accounts to existing users with same email
# BUT require confirmation first (don't auto-connect for new signups)
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False  # Changed to False to show signup form

# Google OAuth2 settings
# Note: OAuth credentials are configured in the database via Django Admin
# (Sites > Social Applications) to avoid duplication
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

# ============================================================================
# CELERY CONFIGURATION
# ============================================================================

CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Manila'
CELERY_ENABLE_UTC = True

# PhilSys Verification Settings
PHILSYS_VERIFICATION_ENABLED = True
PHILSYS_VERIFICATION_TIMEOUT = 30000  # 30 seconds
PHILSYS_VERIFICATION_MAX_RETRIES = 2
PHILSYS_VERIFICATION_RATE_LIMIT = '10/m'  # 10 per minute