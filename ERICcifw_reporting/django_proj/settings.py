# Django settings for django_proj project.
import os.path
import ldap
import ast
import paramiko

from django_auth_ldap.config import LDAPSearch
from ciconfig import CIConfig

paramiko.util.log_to_file("/dev/null")

config = CIConfig()
DEBUG = bool(int(config.get("CIFWK", "debug")))
TEMPLATE_DEBUG = DEBUG

#Note: two email addresses required minimum
ADMINS = ast.literal_eval(config.get("CIFWK", "admins"))

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = config.get("CIFWK", "email_host")
DEFAULT_FROM_EMAIL = config.get("CIFWK", "server_email")
SERVER_EMAIL = config.get("CIFWK", "server_email")

# Get DB Info
dbName = config.get("CIFWK", "dbName")
defaultDBUser = config.get("CIFWK", "defaultDBUser")
dbPassword = config.get("CIFWK", "dbPassword")
dbHost = config.get("CIFWK", "dbHost")
dbPort = config.get("CIFWK", "dbPort")
storageEngine = config.get("CIFWK", "storageEngine")

MANAGERS = ADMINS

if DEBUG == False:
    # This setting is now required whenever DEBUG is False, or else django.http.HttpRequest.get_host() will raise SuspiciousOperation.
    ALLOWED_HOSTS = ['*']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'OPTIONS': { 'init_command': storageEngine },
        'NAME': dbName,                     # Or path to database file if using sqlite3.
        'USER': defaultDBUser,                     # Not used with sqlite3.
        'PASSWORD': dbPassword,                # Not used with sqlite3.
        'HOST': dbHost,                           # Set to empty string for localhost. Not used with sqlite3.
        'PORT': dbPort,                           # Set to empty string for default. Not used with sqlite3.
    },
    # 'validatedb': {
    #     'ENGINE': 'django.db.backends.mysql', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    #     'OPTIONS': { 'init_command': 'SET storage_engine=INNODB;' },
    #     'NAME': 'cifwkdb_schtest_syncdb',                     # Or path to database file if using sqlite3.
    #     'USER': 'schtestusr',                     # Not used with sqlite3.
    #     'PASSWORD': '',                # Not used with sqlite3.
    #     'HOST': '',                           # Set to empty string for localhost. Not used with sqlite3.
    #     'PORT': '',                           # Set to empty string for default. Not used with sqlite3.
    # }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Dublin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-ie'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = 'assets/images'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'images/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/proj/lciadm100/cifwk/latest/django_proj/cireports/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'assets')),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 't1+gowwtd3(!s&s4-1(yqoso+(-fkq+_wx=woo7t@jv71t*6+*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'timelog.middleware.TimeLogMiddleware'
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #os.path.join(os.path.dirname(__file__), 'cireports/templates').replace('\\','/'),
    os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/'),
    config.get("CPI","cpiLibPath"),
    config.get("REPORT", "filePath")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
    'rest_framework',
    'cireports',
    'avs',
    'dmt',
    #'depmodel',
    'fwk',
    'fem',
    'guardian',
    'vis',
    'excellence',
    'foss',
    'depmodel',
    'cpi',
    'mptt',
    'metrics',
    'virtual',
    'cloud',
    'fastcommit',
    'angularVis',
    'timelog',
    'rest_framework_swagger'
)

TIMELOG_LOG = '/tmp/timelog.log'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'plain': {
          'format': '%(asctime)s %(message)s'
        },
        'verbose': {
            'format': '%(asctime)s [%(levelname)s][%(module)s.%(funcName)s:%(lineno)d] %(message)s'
         },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django_auth_ldap': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
        },
        'cireports': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'fwk': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'dmt': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'vis': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'fem': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'excellence': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'foss': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'metrics': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'avs': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'depmodel': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'cpi': {
            'handlers':['console'],
            'level':'INFO',
        },
        'virtual': {
            'handlers':['console'],
            'level':'INFO',
        },
        'cloud': {
            'handlers':['console'],
            'level':'INFO',
        },
    }
}

TIMELOG_ENABLED = bool(int(config.get("CIFWK", "timelog")))
if TIMELOG_ENABLED:
    LOGGING['loggers']['timelog.middleware'] = {
        'handlers': ['timelog'],
        'level': 'INFO',
        'propagate': False,
    }
    LOGGING['handlers']['timelog'] = {
        'level': 'INFO',
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': TIMELOG_LOG,
        'maxBytes': 1024 * 1024 * 5,
        'backupCount': 5,
        'formatter': 'plain',
    }

# Format date and times in an easy-to-read fashion
USE_L10N = False
DATETIME_FORMAT = "Y-m-d H:i:s"

import logging
logger = logging.getLogger('django_auth_ldap')
#logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

AUTHENTICATION_BACKENDS = (
    'cireports.ldap.LDAPBackendInternal',
    'cireports.ldap.LDAPBackendExternal',
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend',
)

# django-guardian setting
ANONYMOUS_USER_ID = -1

#Global LDAP 
AUTH_LDAP_GLOBAL_OPTIONS = {ldap.OPT_X_TLS_REQUIRE_CERT: False}

#LDAP for internal signum
AUTH_LDAP_INTERNAL_SERVER_URI = config.get("LDAP_INTERNAL", "server_url")
AUTH_LDAP_INTERNAL_BIND_DN = config.get("LDAP_INTERNAL", "bind_dn")
AUTH_LDAP_INTERNAL_BIND_PASSWORD = config.get("LDAP_INTERNAL", "password")
AUTH_LDAP_INTERNAL_USER_SEARCH = LDAPSearch(config.get("LDAP_INTERNAL", "search_base"),
            ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
AUTH_LDAP_INTERNAL_USER_DN_TEMPLATE = "uid=%(user)s," + config.get("LDAP_INTERNAL", "dn_template")

#LDAP for Xid's
AUTH_LDAP_EXTERNAL_SERVER_URI = config.get("LDAP_EXTERNAL", "server_url")
AUTH_LDAP_EXTERNAL_BIND_DN = config.get("LDAP_EXTERNAL", "bind_dn")
AUTH_LDAP_EXTERNAL_BIND_PASSWORD = config.get("LDAP_EXTERNAL", "password")
AUTH_LDAP_EXTERNAL_USER_SEARCH = LDAPSearch(config.get("LDAP_EXTERNAL", "search_base"),
            ldap.SCOPE_SUBTREE, "(uid=%(user)s)")
AUTH_LDAP_EXTERNAL_USER_DN_TEMPLATE = "uid=%(user)s," + config.get("LDAP_EXTERNAL", "dn_template")

LOGIN_URL="/login/"
# Default redirect to the root - this is overriden if the user comes in from elsewhere
LOGIN_REDIRECT_URL = "/"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 2592000
    }
}

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
   'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'EXCEPTION_HANDLER': 'exceptionhandler.custom_exception_handler',
}

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)
