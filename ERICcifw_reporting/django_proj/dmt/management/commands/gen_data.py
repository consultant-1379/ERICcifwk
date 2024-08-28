from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import random

from dmt.models import *

import dmt.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Manage a server"
    option_list = BaseCommand.option_list  + (
            make_option('--quiet',
                dest='verbose', action='store_false', default=True,
                help='Stop all informational output'),
            make_option('--nclusters',
                dest='nclusters',
                help='number of clusters to generate'),
            make_option('--mgtsvr',
                dest='mgtsvr',
                help='Management server to assign the clusters to'),
            )


    def handle(self, *args, **options):
        if options['nclusters'] == None:
            raise CommandError("You must supply the hostname of a server to manage")

        if options['nclusters']:
            print "Adding " + options['nclusters'] + " clusters"
            print "Getting mgt server " + options["mgtsvr"]
            mgt = ManagementServer.objects.get(hostname=options["mgtsvr"])

            for c in range(int(options['nclusters'])):
                print "Cluster " + str(c)
                cluster = Cluster(name="TestCluster " + str(c), tipc_address=dmt.utils.getLowestAvailableTIPCAddress(),management_server=mgt)
                cluster.save()
                nservers = random.randint(1,10)
                for s in range(nservers):
                    srv = Server(hostname="cl" + str(c) + "hst" + str(s),
                            domain_name="athtem.eei.ericsson.se",
                            dns_server="159.107.173.3",
                            type="cluster_node",
                            hardware_type="virtual",
                            cluster=cluster)
                    srv.save()
                    # Add a few NICs
                    for n in range(1, 3):
                        macAddress = dmt.utils.getLowestAvailableMacAddress()
                        nic = NetworkInterface(server=srv, mac_address=macAddress)
                        nic.save()
