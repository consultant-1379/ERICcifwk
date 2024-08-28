from avs.models import *
from django.contrib import admin

import logging
logger = logging.getLogger(__name__)

admin.site.register(ActionPoint)
admin.site.register(AVSFile)
admin.site.register(AVS)
admin.site.register(Epic)
admin.site.register(TestCase)
admin.site.register(UserStory)
admin.site.register(VerificationPoint)
admin.site.register(TestResult)
