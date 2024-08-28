from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
from dmt.models import *

import dmt.utils
import dmt.buildconfig
import fwk.utils
import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to generate the Configuration file which can be used for the auto Deployment
    '''
    help = "The purpose of this program is to generate the Configuration file which can be used for the auto Deployment"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            make_option('--tor_ver',
                dest='torVersion',
                help='The version of the Tor Release which is loaded on the LMS (e.g. "1.0.14")'),
            )

    def handle(self, *args, **options):
        if options['clusterId'] == None:
            raise CommandError("To run this option you need to specify the ID of the Cluster to configure")
        if options['torVersion'] == None:
            raise CommandError("To run this option you need to specify the tor Version of the ISO you wish to Install e.g 1.0.14")

        # Defining the drop if not specified then take latest    
        clusterId = options['clusterId']
        torVersion = options['torVersion']
        torVersion = torVersion.lower()
        
        # Wrapper script for calling all function in a defined order
        dmt.buildconfig.generateConfigFile(clusterId, torVersion)
