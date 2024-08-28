from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List all locations in our cloud organisation"
    option_list = BaseCommand.option_list  + (
            make_option('--location',
                dest='location',
                help='name of the node to list'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        if options['location'] != None:
            print "Request for location:" + options['location']
            locations = driver.list_locations()
            for location in locations:
                if location.name == options['location']:
                    self.printImage(location)
        else:
            locations = driver.list_locations()
            for location in locations:
                self.printImage(location)

    def printImage(self, location):
        print " Location Name: " + str(location.name)
        print " Country: " + str(location.country)
        print "\n"
