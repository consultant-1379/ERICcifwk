from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
#logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List all nodes in our cloud organisation"
    option_list = BaseCommand.option_list  + (
            make_option('--node',
                dest='node',
                help='name of the node to list'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        if options['node'] != None:
            print "Request for node:" + options['node']
            nodes = driver.list_nodes()
            for node in nodes:
                if node.name == options['node']:
                    self.printNode(node)
        else:
            nodes = driver.list_nodes()
            for node in nodes:
                self.printNode(node)

    def printNode(self, node):
        print " Node Name: " + str(node.name)
        print "      UUID: " + str(node.uuid)
        state = "UNKNOWN"
        if (node.state == NodeState.RUNNING):
            state = "RUNNING"
        elif (node.state == NodeState.REBOOTING):
            state = "REBOOTING"
        elif (node.state == NodeState.TERMINATED):
            state = "TERMINATED"
        elif (node.state == NodeState.PENDING):
            state = "PENDING"
        print "     State: " + state
        print "    Driver: " + str(node.driver)
        print "Extra: "
        for k, v in node.extra.items():
            print "            " + k + ": " + str(v)
        print "Public IPs: "
        for ip in node.public_ips:
            print "            " + str(ip)
        print "Private IPs: "
        for ip in node.private_ips:
            print "            " + str(ip)
        print "\n"
