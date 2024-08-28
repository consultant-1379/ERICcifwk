from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from dmt.utils import *
from dmt.models import *
from cireports.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            ddList = DeploymentDescription.objects.filter(name__endswith="production")
            for dd in ddList:
                dd.capacity_type="production"
                dd.save()
        except Exception as e:
            raise CommandError("Error found - " + str(e))


