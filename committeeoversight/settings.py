"""
Django settings for committeeoversight project.

Generated by 'django-admin startproject' using Django 2.1.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from .local_settings import *

if DEBUG is False:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    def before_send(event, hint):
        """
        Log 400 Bad Request errors with the same custom fingerprint so that we can
        group them and ignore them all together. See:
        https://github.com/getsentry/sentry-python/issues/149#issuecomment-434448781
        """
        log_record = hint.get('log_record')
        if log_record and hasattr(log_record, 'name'):
            if log_record.name == 'django.security.DisallowedHost':
                event['fingerprint'] = ['disallowed-host']
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        before_send=before_send,
        integrations=[DjangoIntegration()]
    )

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Application definition

INSTALLED_APPS = [
    'committeeoversightapp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'opencivicdata',
    'opencivicdata.core',
    'opencivicdata.legislative',
    'crispy_forms',
    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail.core',
    'modelcluster',
    'taggit',
    'wagtail.contrib.modeladmin',
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'wagtail.core.middleware.SiteMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

ROOT_URLCONF = 'committeeoversight.urls'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'committeeoversight.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Chicago'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

try:
    from committeeoversight.local_settings import MEDIA_ROOT
except ImportError:
    # If no MEDIA_ROOT is configured, default to storing user uploads in
    # the current working directory
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_URL = '/media/'

# Redirect to home URL after login (Default redirects to /accounts/profile/)
LOGIN_REDIRECT_URL = '/'

WAGTAIL_SITE_NAME = 'Committee Oversight'

WAGTAIL_MODERATION_ENABLED = False

DEFAULT_CONGRESS_INACTIVE_DAYS = 62

CURRENT_PERMANENT_COMMITTEES = [
    'House Committee on Agriculture',
    'House Committee on Appropriations',
    'House Committee on Armed Services',
    'House Committee on Budget',
    'House Committee on Education and the Workforce',
    'House Committee on Energy and Commerce',
    'House Committee on Financial Services',
    'House Committee on Foreign Affairs',
    'House Committee on Homeland Security',
    'House Committee on House Administration',
    'House Committee on Intelligence (Permanent Select)',
    'House Committee on Judiciary',
    'House Committee on Natural Resources',
    'House Committee on Oversight and Government Reform',
    'House Committee on Rules',
    'House Committee on Science, Space, and Technology',
    'House Committee on Small Business',
    'House Committee on Transportation and Infrastructure',
    'House Committee on Veterans\' Affairs',
    'House Committee on Ways and Means',
    'Senate Committee on Aging',
    'Senate Committee on Agriculture, Nutrition, and Forestry',
    'Senate Committee on Appropriations',
    'Senate Committee on Armed Services',
    'Senate Committee on Banking, Housing, and Urban Affairs',
    'Senate Committee on Budget',
    'Senate Committee on Commerce, Science, and Transportation',
    'Senate Committee on Energy and Natural Resources',
    'Senate Committee on Environment and Public Works',
    'Senate Committee on Finance',
    'Senate Committee on Foreign Relations',
    'Senate Committee on Health, Education, Labor, and Pensions',
    'Senate Committee on Homeland Security and Governmental Affairs',
    'Senate Committee on Indian Affairs',
    'Senate Committee on Intelligence',
    'Senate Committee on Judiciary',
    'Senate Committee on Rules and Administration',
    'Senate Committee on Small Business and Entrepreneurship',
    'Senate Committee on Veterans\' Affairs',
]

CHAMBERS = [
    'United States House of Representatives',
    'United States Senate'
]

DISPLAY_CATEGORIES = [
    'Nominations',
    'Legislative',
    'Policy',
    'Agency Conduct',
    'Private Sector Oversight',
    'Fact Finding',
    'Field',
    'Closed',
]
