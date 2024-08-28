from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List all appNames in our cloud organisation"
    option_list = BaseCommand.option_list  + (
            make_option('--appName',
                dest='appName',
                help='name of the appName to list'),
            )

    def handle(self, *args, **options):
        if options['appName'] == None:
            raise CommandError("To run this option you need to specify the APP Name")

        driver = dmt.cloud.auth()
        print dmt.cloud.getGatewayInfo(driver, options['appName'], "getGatewayIp")
