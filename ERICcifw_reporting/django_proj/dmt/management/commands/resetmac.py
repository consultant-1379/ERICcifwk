from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Update LITP Gateway MAC Address"
    option_list = BaseCommand.option_list  + (
            make_option('--appName',
                dest='appName',
                help='name of the appName to list'),
            make_option('--nicid',
                dest='nicid',
                help='ID of the NIC we want to reset the MAC address on'),
            )

    def handle(self, *args, **options):
        if options['appName'] == None:
            raise CommandError("To run this option you need to specify the APP Name")
        if options['nicid'] == None:
            raise CommandError("To run this option you need to specify the NIC ID of the Gateway")

        driver = dmt.cloud.auth()
        dmt.cloud.resetGatewayMac(driver,options['appName'],options['nicid'])

