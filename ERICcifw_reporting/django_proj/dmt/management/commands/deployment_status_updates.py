from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            clusters = Cluster.objects.all()
            status = DeploymentStatusTypes.objects.get(status="IDLE")
            for clust in clusters:
                logger.info("Cluster: " + str(clust.name))
                deplyStatus = DeploymentStatus.objects.get_or_create(cluster=clust, status=status)
                logger.info("Status: " + str(deplyStatus))
        except Exception as e:
            raise CommandError("Error found - " + str(e))


