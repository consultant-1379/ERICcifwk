from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Start the given vAPP in the cloud organisation"
    option_list = BaseCommand.option_list  + (
            make_option('--node',
                dest='node',
                help='name of the node to start'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        nodeinst = dmt.cloud.getNode(driver, options['node'])
        driver.ex_deploy_node(nodeinst)
