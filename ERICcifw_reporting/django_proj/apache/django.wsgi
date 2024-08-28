import os, sys

apache_configuration = os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace)

sys.path.append(workspace + "/django_proj")

os.environ['DJANGO_SETTINGS_MODULE'] = 'django_proj.settings'

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
