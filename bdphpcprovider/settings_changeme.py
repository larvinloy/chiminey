import djcelery
from datetime import timedelta

DEBUG=True

# Django settings for the SMRA project deployed under runserver

from os import path

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

#SUB_SITE = "bdphpcprovider"

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': path.join(path.dirname(__file__),'db/django.sql').replace('\\','/'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}


# Celery queue uses Django for persistence
BROKER_TRANSPORT = 'django'


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

STATIC_DOC_ROOT = path.join(path.dirname(__file__),
                               'smartconnectorscheduler/site_media').replace('\\', '/')

#STATIC_URL = path.join(path.dirname(__file__),'smra_portal/site_media').replace('\\','/')
#STATIC_URL = path.join('/site_media/').replace('\\','/')

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = '/site_media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
#ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'lpw@bqiq#lwcx0w=xo=j@z9#h!d&8svwz5fwv0_j1319^%92p_'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.transaction.TransactionMiddleware'
)

ROOT_URLCONF = 'bdphpcprovider.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    path.join(path.dirname(__file__),
    'smartconnectorscheduler/templates/').replace('\\','/'),
    path.join(path.dirname(__file__),
    'smartconnectorscheduler/publish/').replace('\\','/'),
    path.join(path.dirname(__file__),
    'simpleui/templates/').replace('\\','/'),
)

TEMPLATE_CONTEXT_PROCESSORS = ("django.contrib.auth.context_processors.auth",
"django.core.context_processors.debug",
"django.core.context_processors.i18n",
"django.core.context_processors.media",
"django.core.context_processors.static",
"django.core.context_processors.tz",
'django.core.context_processors.request',
"django.contrib.messages.context_processors.messages")

OUR_APPS = ('bdphpcprovider.smartconnectorscheduler',
    'bdphpcprovider.simpleui')

def get_admin_media_path():
    import pkgutil
    package = pkgutil.get_loader("django.contrib.admin")
    return path.join(package.filename, 'static', 'admin')

ADMIN_MEDIA_STATIC_DOC_ROOT = get_admin_media_path()

# Static content location
STATIC_URL = '/static/'

# Used by "django collectstatic"
STATIC_ROOT = path.abspath(path.join(path.dirname(__file__),'..','static'))

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = STATIC_URL + '/admin/'

STATICFILES_DIRS = (
    ('admin', ADMIN_MEDIA_STATIC_DOC_ROOT),
)


AUTH_PROFILE_MODULE='smartconnectorscheduler.UserProfile'


INSTALLED_APPS = (
    'django_extensions',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.markup',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'south',
    'storages',
    'djcelery',
    'djkombu',
    'tastypie',
    'django_nose',
    'widget_tweaks'

) + OUR_APPS


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            #'format': '%(levelname)s %(message)s'
        },
    },

    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file1': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': './bdphpcprovider.log',
            'formatter': 'simple'
        },
        'file2': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/var/log/cloudenabling/celery/celeryd.log',
            'formatter': 'simple'
        },
    },

    'loggers': {
        'bdphpcprovider.smartconnectorscheduler': {
            'handlers': ['console', 'file1'],
            'level': 'DEBUG',
            },
         'celery': {
             'handlers': ['console', 'file2'],
             'level': 'DEBUG',
             },
         'bdphpcprovider.core':{
             'handlers': ['console', 'file1'],
             'level': 'DEBUG'
         },
        },
}

TASTYPIE_DEFAULT_FORMATS = ['json']

FIXTURE_DIRS = (
                path.join(path.dirname(__file__),
                               'smartconnectorscheduler/site_media').replace('\\', '/'),)


AUTH_PROFILE_MODULE = "smartconnectorscheduler.UserProfile"

LOGIN_URL = '/accounts/login'

SFTP_STORAGE_HOST = ""
SFTP_STORAGE_ROOT = ""
SFTP_STORAGE_PARAMS = {}

#CELERYBEAT_SCHEDULER="djcelery.schedulers.DatabaseScheduler"
# Warning: celeryd is not safe for muliple workers when backed by sqlite
CELERYBEAT_SCHEDULE = {
    #"test": {
    #    "task": "smartconnectorscheduler.test",
    #    "schedule": timedelta(seconds=15),
    #},
    "run_contexts": {
        "task": "smartconnectorscheduler.run_contexts",
        "schedule": timedelta(seconds=60)
      },
    }

#CELERYD_OPTS = "--time-limit=10"

FILE_UPLOAD_PERMISSIONS = 0700

# A MyTardis API endopoint
TEST_MYTARDIS_IP = ""
TEST_MTARDIS_USER = ""
TEST_MYTARDIS_PASSWORD = ""

djcelery.setup_loader()





