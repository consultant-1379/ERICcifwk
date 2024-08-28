from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Get information associated with IP address"
    option_list = BaseCommand.option_list  + (
            make_option('--ip',
                dest='ip',
                help='ip address'),
            )

    def handle(self, *args, **options):
        result=dmt.utils.getIPinformation(options['ip'])
        print "\n\n**********IP Details**********"
        print "IP: " +str(result['ip'])
        print "Server: " +str(result['server'])
        print "MAC address: " +str(result['mac'])
        print "Server Instance: " +str(result['serviceinst'])
        print "Cluster: " +str(result['cluster'])
