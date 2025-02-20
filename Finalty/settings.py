"""
Django settings for Finalty project.

Generated by 'django-admin startproject' using Django 4.1.9.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-od+82(4(e(i7t$9iwe%l(v^^t@xwfr!-28u73)sa0c(o+m(bf="

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', '.vercel.app', '.now.sh','*']


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'base',
    'meta',
    'robots_txt',
    'corsheaders',
]   

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'corsheaders.middleware.CorsMiddleware',
    'base.middlewares.UserDataMiddleware',
    'base.middlewares.CalendlyUserMiddleware',
]

ROOT_URLCONF = "Finalty.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Finalty.wsgi.application"


DATABASES = {
   'default': {
       'ENGINE': 'djongo',
       'CLIENT': {
           
        #    'host': "mongodb+srv://nagi:nagi@cluster0.ohv5gsc.mongodb.net/LogManagement",
           'host': "mongodb+srv://ciddarth:applexc@cluster0.mg1di.mongodb.net/CalendlyDjango",
           'name':'CalendlyDjango',
           'authMechanism': "SCRAM-SHA-1",
        }
   }
}

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.sqlite3",
#         "NAME": BASE_DIR / "db.sqlite3",
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

import os

STATIC_URL = 'static/'
STATICFILES_DIRS = os.path.join(BASE_DIR, 'static'),
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_build')

MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
MEDIA_URL = '/media/'


# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = '/login/'

# Redirect to this URL after login
LOGIN_REDIRECT_URL = '/dashboard/'

# Redirect to this URL after logout
LOGOUT_REDIRECT_URL = '/g_login/'

import os

GOOGLE_CLIENT_SECRETS_FILE = os.path.join(BASE_DIR, 'client_secret.json')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid',
]
GOOGLE_REDIRECT_URI = 'https://django-acuity-scheduling.vercel.app/google/callback/'

CORS_ALLOW_ALL_ORIGINS = True

X_FRAME_OPTIONS = 'ALLOWALL'
CSRF_COOKIE_SAMESITE = 'None'  # Allow the CSRF cookie to be sent in cross-origin requests
CSRF_COOKIE_SECURE = True      # Set this to True if you're using HTTPS
SESSION_COOKIE_SAMESITE = 'None'  # SameSite for session cookies
SESSION_COOKIE_SECURE = True   # Secure the session cookie if using HTTPS


# Acuity Scheduling

CALENDLY_WEBHOOK_EVENTS = [
    {"event": "appointment.rescheduled", "target": "https://yourwebhookendpoint.com/rescheduled"},
    {"event": "appointment.scheduled", "target": "https://yourwebhookendpoint.com/scheduled"},
    {"event": "appointment.canceled", "target": "https://yourwebhookendpoint.com/canceled"},
]

# Calendly Custom Fields
CALENDLY_CUSTOM_FIELDS = [
    "Calendly Client Link",
    "Calendly ID",
    "Calendly Agent Link",
    "Calendly Calendar Name",
    "Calendly Calendar Email",
    "Calendly Event Price"
]

# Zoho credentials

CLIENT_ID = "1000.MCX6SMTW5Q67KGR4W193Z0I214HNMX"
CLIENT_SECRET = "cf968b526f3772b955030f0569391419784a45a9b3"
ZOHO_API_BASE_URL = "https://www.zohoapis.com/crm/v2"
REDIRECT_URI = "http://127.0.0.1:8000/zoho-callback/"

SCOPE = "ZohoCRM.settings.fields.ALL,ZohoCRM.settings.fields.CREATE,ZohoCRM.users.READ,ZohoCRM.settings.fields.READ,ZohoCRM.org.READ,ZohoCRM.modules.READ,ZohoCRM.modules.CREATE,ZohoCRM.modules.UPDATE,ZohoSearch.securesearch.READ,ZohoCRM.settings.custom_views.READ,ZohoCRM.settings.modules.READ,ZohoCRM.modules.ALL,ZohoCRM.signals.ALL"


# Calendly OAuth settings
CALENDLY_CLIENT_ID = 'mmgzH3MGHOl4XxSo_S2Rd88NHkQXNtp2BB1oBcHue_s'
CALENDLY_CLIENT_SECRET = 'QHe1XUACtSPN_QGEgr7oMfn5xDspp6nBZ-A3YCpawtY'
CALENDLY_REDIRECT_URI = 'http://localhost:8000/oauth/callback/'
CALENDLY_WEBHOOK_URI="x-im4xCjbY-adPbU8CvMF088AdwhA-GQeMlAR7MI3RE"

