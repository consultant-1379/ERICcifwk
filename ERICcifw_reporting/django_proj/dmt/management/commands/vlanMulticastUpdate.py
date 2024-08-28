from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from dmt.models import *

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def handle(self, *args, **options):
        try:
            multicastTypesDict = { "BR0": "SVC VLAN", "BR3":"JGroups VLAN" }
            clusterServers = ClusterServer.objects.filter(node_type__startswith="SVC")
            for k, v in multicastTypesDict.iteritems():
                if not VlanMulticastType.objects.filter(name=str(k)).exists():
                    multicastType = VlanMulticastType.objects.create(name=str(k), description=str(v))
                    logger.info("Vlan Multicast Type Created: " + str(multicastType))
            multicastTypesList = VlanMulticastType.objects.all()
            for clustSer in clusterServers:
                logger.info("Cluster Server: " + str(clustSer.server.hostname))
                for item in multicastTypesList:
                    if "BR0" in str(item.name):
                        VlanMulticast.objects.create(clusterServer=clustSer, multicast_type=item, multicast_snooping="1", multicast_querier="1", multicast_router="2", hash_max="2048")
                    elif "BR3" in str(item.name):
                        VlanMulticast.objects.create(clusterServer=clustSer, multicast_type=item, multicast_snooping="0", multicast_querier="0", multicast_router="1", hash_max="512")
                logger.info("Vlan Multicasts Created: " + str(VlanMulticast.objects.filter(clusterServer=clustSer)))
        except Exception as e:
            raise CommandError("Error found - " + str(e))


