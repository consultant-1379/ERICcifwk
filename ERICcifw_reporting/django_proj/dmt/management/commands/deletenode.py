from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Delete a node (vApp)"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='name',
                help='the name of the node to delete'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        nodes = driver.list_nodes()
        node = [i for i in nodes if i.name == options['name']][0]
        driver.destroy_node(node)
