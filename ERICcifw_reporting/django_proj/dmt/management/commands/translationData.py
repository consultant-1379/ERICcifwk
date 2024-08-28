from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *
from cireports.models import *
from distutils.version import StrictVersion

import sys, os, tempfile, shutil, time
import dmt.deploy
import dmt.utils
import cireports.models
import logging
import signal
import warnings

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

def handler(signum, frame):
    logger.info("Captured Key Stroke")
    descriptionDetails = "Caught Ctrl-C Command, Cleaned up the system"
    dmt.utils.dmtError(descriptionDetails)

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to execute translatable functions to collect language data from ENM deployments
    The function collects the data, tars, zips the data and deploys to Nexus and the CI portal
    '''
    help = "Class to execute function to collect Translatable Data from an ENM Deployment"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            make_option('--product',
                dest='product',
                help='Product Area for Deployed System'),

            )

    def handle(self, *args, **options):

        signal.signal(signal.SIGINT, handler)
        # Set the default for the status

        if options['clusterId'] == None:
            raise CommandError("Please enter the cluster Id")
        else:
            clusterId = options['clusterId']

        if options['product'] == None:
            raise CommandError("Please enter the Product Area for the Deployment")
        else:
            product = options['product']


        if product == 'ENM':
            returnCode = dmt.utils.tanslationData(clusterId, product)
            if returnCode !=0:
                raise CommandError("There was an issue running the Get Translation Data function for ENM")
        else:
            raise CommandError("Get Translation Data is only for use for ENM")
