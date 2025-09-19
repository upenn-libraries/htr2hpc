################################################################################
# Based on Princeton CDH Ansible eScriptorium local_settings template. See
#
# - inventory/group_vars/htr_staging/vars.yml, permalink:
#   - https://github.com/Princeton-CDH/cdh-ansible/blob/882f32c9a38886c22be59fe1ce1c7d74142c4ccb/roles/django/templates/escriptorium_settings.py.j2
# - roles/django/templates/escriptorium_settings.py.j2, permalink:
#   - https://github.com/Princeton-CDH/cdh-ansible/blob/882f32c9a38886c22be59fe1ce1c7d74142c4ccb/inventory/group_vars/htr_staging/vars.yml#L67
#
#
################################################################################
import os

from escriptorium.settings import *
from htr2hpc.settings import *

from django.utils.translation import gettext_lazy as _


# DEBUG = True

# enable french and german
LANGUAGES = [
    ('en', _('English')),
    ('fr', _('French')),
    ('de', _('German'))
]

# disables cache for dev env
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#     }
# }

# NOTE: not overriding eScriptorium settings.py
# Cryptographic key for signing secrets. Keep the production key hidden!
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# SECRET_KEY = "{{ django_secret_key }}"

# NOTE: not overriding eScriptorium settings.py
# Display detailed error messages. Turn off in production!
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
# DEBUG = {{ django_debug }}

# NOTE: not overriding eScriptorium settings.py
# Valid hostnames this site can serve.
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
# ALLOWED_HOSTS = [{% for host in django_allowed_hosts %}"{{ host }}", {% endfor %}]

CSRF_TRUSTED_ORIGINS = ["https://*.upenn.edu", "http://localhost:8000"]

# Use x-forwarded-proto header to tell if request from nginx was https or not
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# NOTE: Not needed; we don't have QA sites
# Show a small "this is a test site" banner for QA sites, if corresponding
# template and stylesheet are present.
# SHOW_TEST_WARNING = {{ django_test_warning }}

# NOTE: Not overriding eScriptorium settings.py
# {% if media_root is defined %}
# # Configure media root path
# MEDIA_ROOT = '{{ media_root }}'
# {% endif %}

# NOTE: Not overriding eScriptorium settings.py
# # Database configuration
# # https://docs.djangoproject.com/en/dev/ref/databases/
# {% block db_config %}
# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.{{ django_db_backend }}",
#         "NAME": "{{ django_db_name }}",
#         "USER": "{{ django_db_user }}",
#         "PASSWORD": "{{ django_db_password }}",
#         "HOST": "{{ django_db_host }}",
#     },
# }
# {% endblock %}

# NOTE: Not using PU auth
# Princeton CAS configuration (authentication, user account creation)
# https://github.com/Princeton-CDH/django-pucas
# {% block cas_config %}
# CAS_SERVER_URL = "https://fed.princeton.edu/cas/"
# CAS_VERSION = "3"
# PUCAS_LDAP.update({
#     "SERVERS": [
#         "ldap2.princeton.edu",
#         "ldap3.princeton.edu",
#         "ldap4.princeton.edu",
#         "ldap5.princeton.edu"
#     ],
#      "SEARCH_BASE": "o=Princeton University,c=US",
#      "SEARCH_FILTER": "(uid=%(user)s)",
# })
# {% endblock %}


# NOTE: Using eScriptorium defaults for most of these
# Email configuration (error messages, admin notifications)
# https://docs.djangoproject.com/en/dev/howto/error-reporting/
# https://docs.wagtail.io/en/latest/reference/settings.html#email-notifications
# {% block email_config %}
# ADMINS = [("CDH Dev Team", "cdhdevteam@princeton.edu")]
# SERVER_EMAIL = "cdhdevteam@princeton.edu"
SERVER_EMAIL = os.getenv('SERVER_EMAIL', 'user@example.com')
# # eScriptorium uses a non-standard from email configuration; use same for now
DEFAULT_FROM_EMAIL = SERVER_EMAIL
# # use PUL pony express relay
# EMAIL_HOST = "lib-ponyexpr-prod.princeton.edu"
# EMAIL_SUBJECT_PREFIX = "{{ django_email_subject }}"
EMAIL_SUBJECT_PREFIX = os.getenv('EMAIL_SUBJECT_PREFIX', 'eScriptorium')
# EMAIL_USE_TLS = False
# #EMAIL_PORT = 587  # use default 25
# {% endblock %}

# NOTE: Changing PU log config to stream to stdout
# Logging configuration
# https://docs.djangoproject.com/en/dev/topics/logging/
# Solution following https://stackoverflow.com/a/9541647
# Sends a logging email even when DEBUG is on
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'basic': {
            'format': '[%(asctime)s] %(levelname)s:%(name)s::%(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S',
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True
        },
        'debug_log': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'basic'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'debug_log'],
            'level': 'ERROR',
            'propagate': True,
        },
        '{{ django_app }}': {
            'handlers': ['debug_log'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'htr2hpc': {
            'handlers': ['debug_log'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}


# NOTE: Not configuring search
# # Solr configuration (search index)
# # https://github.com/Princeton-CDH/parasolr
# {% block solr_config %}
# {% if solr_collection is defined %}
# SOLR_CONNECTIONS = {
#     'default': {
#         'URL': '{{ solr_url }}',
#         'COLLECTION': '{{ solr_collection }}',
#         'CONFIGSET': '{{ solr_configset }}'
#     }
# }
# {% endif %}
# {% endblock %}

# Force HTTPS
DEFAULT_SCHEME = 'https'
# Following https://stackoverflow.com/a/68310760
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Extra app-specific configuration
# custom config for htr2hpc
HPC_HOSTNAME = os.getenv('HPC_HOSTNAME', 'localhost')
# copied in place by escriptorium_setup role
HPC_SSH_KEYFILE = os.getenv('HPC_SSH_KEYFILE', '~/.ssh/id_rsa')
HPC_WORKING_DIR = os.getenv('HPC_WORKING_DIR', None)
HPC_SSH_USER = os.getenv('HPC_SSH_USER', None)
