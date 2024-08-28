"""
WSGI config for myproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""


import os, sys

apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)

sys.path.append(workspace + "/django_proj")
sys.path.append(workspace + "/lib/python/site-packages")
sys.path.append(workspace + "/lib/python")

os.environ['REQUESTS_CA_BUNDLE'] = '/etc/ssl/certs/ca-bundle.crt'
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_proj.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

