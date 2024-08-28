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
        if options['node'] != None:
            if not options['comment']:
                print "To run this option you need to specify the VAPP comment (--comment \"Comment\""
                print "Because the VAPP comment is not specified this option will now exit"
                sys.exit()
            else:
                print "Request for node:" + options['node']
                print "Comment:" + options['comment']
                comment=options['comment']
                nodes = driver.list_nodes()
                for node in nodes:
                    if node.name == options['node']:
                        dmt.cloud.kbgVmNetInfo(comment,node)
        else:
            print "To run this option you need to specify the VAPP (--node <VAPP>)"
            print "Because the VAPP is not specified this option will now exit"
            sys.exit()
