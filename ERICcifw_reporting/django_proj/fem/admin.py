from fem.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)


admin.site.register(FemURLs)
admin.site.register(FemKGBUrl)
