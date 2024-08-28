from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
import dmt.cloud

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a node (vApp)"
    option_list = BaseCommand.option_list  + (
            make_option('--image',
                dest='image',
                help='name of the image to use'),
            make_option('--name',
                dest='name',
                help='the name of the node to create'),
            )

    def handle(self, *args, **options):
        driver = dmt.cloud.auth()
        images = driver.list_images()
        image = [i for i in images if i.name == options['image']][0]
        node = driver.create_node(name=options['name'], image=image, ex_deploy=False)
