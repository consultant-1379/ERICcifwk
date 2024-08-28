from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *

from libcloud.compute.types import Provider
from libcloud.compute.types import NodeState
from libcloud.storage.types import Provider, ContainerDoesNotExistError
from libcloud.storage.providers import get_driver

import dmt.cloud

import logging
import subprocess
from datetime import datetime
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a Template in the Catalog of this vApp/node instance"
    option_list = BaseCommand.option_list  + (
            make_option('--node',
                dest='node',
                help='name of the node to start'),
            )

    def handle(self, *args, **options):
	driver = dmt.cloud.auth()	
        nodeinst = dmt.cloud.getNode(driver, options['node'])
	container_name = nodeinst.name
	logger.info("Node Instance we are searching on: " + str(container_name))
	storage_driver = get_driver(Provider.CLOUDFILES_US)('username', 'api key')
	try:
    		container = storage_driver.get_container(container_name=container_name)
	except ContainerDoesNotExistError:
    		container = storage_driver.create_container(container_name=container_name)
