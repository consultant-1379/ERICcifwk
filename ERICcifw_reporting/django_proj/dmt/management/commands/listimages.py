from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "List all images in our cloud organisation"
    option_list = BaseCommand.option_list  + (
            make_option('--image',
                dest='image',
                help='name of the node to list'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        if options['image'] != None:
            print "Request for image:" + options['image']
            images = driver.list_images()
            for image in images:
                if image.name == options['image']:
                    self.printImage(image)
        else:
            images = driver.list_images()
            for image in images:
                self.printImage(image)

    def printImage(self, image):
        print " Image Name: " + str(image.name)
        print " Extra: " + str(image.extra)
        print "\n"
