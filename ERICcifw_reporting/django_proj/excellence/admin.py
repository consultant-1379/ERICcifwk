from excellence.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

admin.site.register(Organisation)
admin.site.register(Category)
admin.site.register(Question)
admin.site.register(Answer)
