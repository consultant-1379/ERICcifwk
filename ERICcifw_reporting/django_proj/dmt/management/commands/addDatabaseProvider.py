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
            clusters = Cluster.objects.all()
            for cluster in clusters:
                DeploymentDatabaseProvider.objects.create(cluster=cluster)
        except Exception as e:
            raise CommandError("Error found - " + str(e))


