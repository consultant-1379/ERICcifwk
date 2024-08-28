from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
from dmt.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud
import sys

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    This command is responsible for creating an entry in the CI Framework database
    which defines the network information for a specific vApp passed as an option.

    The use case is for a CI Execution team member who has manually configured
    a vApp and wishes to create a template (catalog entry) from that vApp for the
    CI Framework to use in auto-deployments. Prior to creating the template, the 
    CI Ex team member should execute this script to populate the CI Fwk database with
    the relevant information.

    A potential improvement may be to include the name of the template as an option.
    Another improvement may be to automate the creation of the template as part of
    this script.
    """
    help = "Add Netork info to DB about VAPP"
    option_list = BaseCommand.option_list  + (
            make_option('--node',
                dest='node',
                help='name of the node to list'),
            make_option('--comment',
                dest='comment',
                help='comment for what the node is'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        if options['node'] == None:
            raise CommandError("To run this option you need to specify the VAPP (--node <VAPP>)")
        if not options['comment']:
            raise CommandError("To run this option you need to specify the VAPP comment (--comment \"Comment\"")
        print "Request for node:" + options['node']
        print "Comment:" + options['comment']
        comment=options['comment']
        nodes = driver.list_nodes()
        for node in nodes:
            logger.info("Checking " + str(node.name))
            if node.name == options['node']:
                if (not dmt.cloud.storeCloudTemplateInfo(comment,node)):
                    raise CommandError("Failed to update network information for this vApp")
