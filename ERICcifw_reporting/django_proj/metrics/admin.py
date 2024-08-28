from metrics.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

# Register your models here.

admin.site.register(EventType)
admin.site.register(SPPServer)
