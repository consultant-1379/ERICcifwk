from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            clusters = Cluster.objects.all()
            for clust in clusters:
                logger.info("Cluster: " + str(clust.name))
                logger.info("Cluster Mgt: " + str(clust.management_server.product.name))
                if clust.management_server.product.name == "OSS-RC":
                   clusterLayout = ClusterLayout.objects.get(id=3)
                   logger.info("Cluster Layout: " + str(clusterLayout.id))
                   if clusterLayout:
                       Cluster.objects.filter(id=clust.id).update(layout=clusterLayout)
                else:
                   clusterServer = ClusterServer.objects.filter(cluster=clust)
                   if clusterServer:
                       for cs in clusterServer:
                           logger.info("Cluster Node: " + str(cs.node_type))
                           if "SVC" in cs.node_type or "DB" in cs.node_type or "SCP" in cs.node_type:
                               clusterLayout = ClusterLayout.objects.get(id=1)
                               logger.info("Cluster Layout: " + str(clusterLayout.id))
                               if clusterLayout:
                                   Cluster.objects.filter(id=clust.id).update(layout=clusterLayout)
                               break;
                           elif "SC" in cs.node_type or "PL" in cs.node_type:
                               clusterLayout = ClusterLayout.objects.get(id=2)
                               logger.info("Cluster Layout: " + str(clusterLayout.id))
                               if clusterLayout:
                                   Cluster.objects.filter(id=clust.id).update(layout=clusterLayout)
                               break;
                           else:
                               clusterLayout = ClusterLayout.objects.get(id=2)
                               logger.info("Cluster Layout: " + str(clusterLayout.id))
                               if clusterLayout:
                                   Cluster.objects.filter(id=clust.id).update(layout=clusterLayout)
                   else:
                       clusterLayout = ClusterLayout.objects.get(id=2)
                       logger.info("Cluster Layout: " + str(clusterLayout.id))
                       Cluster.objects.filter(id=clust.id).update(layout=clusterLayout)
        except Exception as e:
            raise CommandError("Error found - " + str(e))


