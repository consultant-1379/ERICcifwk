from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
import dmt.rv_deploy
from dmt.models import *

import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to edit the inventory and definition XML files and validate against the 
    XSD's stored in Nexus
    '''
    help = "Class to edit the inventory and definition XML and validate against XSD's"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            make_option('--installgroup',
                dest='installGroup',
                help='Group identifier for pool of clusters to install from'),
            make_option('--drop',
                dest='drop',
                help='Optional Parameter: The Drop where the packages should be downloaded from (e.g. "1.0.11")'),
            make_option('--tordeploy',
                dest='tordeploy',
                help='Optional Parameter: To set the specific Tor Deploy Script tar file to use for the installation'),
            make_option('--deployPackage',
                dest='package:R-State/Latest',
                help='Optional Parameter: Used if you wish to deploy the system with a specific packages R-State or Latest R-State. Format of input Package:R-State/Latest. Multiple packages can be given in by seperating them with a double colon "::", e.g Package:R-State/Latest::Package:R-State/Latest etc'),
            make_option('--deployRelease',
                dest='deployRelease',
                help='Optional Parameter: Used if you wish to deploy a certain release of the deployment tar file. Default is the 13B'),
            make_option('--cfgTemplate',
                dest='cfgTemplate',
                help='Optional Parameter: Used if you wish to deploy using the cfg template for torinst'),
            )

    def handle(self, *args, **options):

        #Defining the drop if not specified then take latest    
        if options['drop'] == None:
            logger.info("Drop not specified. Taking latest Packages within Nexus")
            drop = "latest"
        else:
            drop = options['drop']

        if options['clusterId'] == None:
            if options['installGroup'] == None:
                raise CommandError("You need to specify either cluster group or cluster ID")
            else:
                clusterId = dmt.utils.getFreeCluster(options['installGroup'])
        else:
            clusterId = options['clusterId']
            clusterObj = Cluster.objects.get(id=clusterId)
            if clusterObj.status == "idle":
                dmt.utils.setClusterStatus(clusterId,"busy")
            else:
                logger.error("This cluster is in a " + str(clusterObj.status) + " state")
                raise CommandError("Cluster " + str(clusterObj.name) + " is " + str(clusterObj.status))

        # Package is set it None if nor specified 
        if options['package:R-State/Latest'] != None:
            packageList = options['package:R-State/Latest']
        else:
            packageList = None

        # Package is set it None if nor specified 
        if options['deployRelease'] != None:
            deployRelease = options['deployRelease']
        else:
            deployRelease = None

        # cfgTemplate is used to declare which cfg file to use for the installation
        if options['cfgTemplate'] != None:
            cfgTemplate = "torinstDeploy"
        else:
            cfgTemplate = "rvDeploy"
        # Defining the drop if not specified then take latest    
        if options['tordeploy'] == None:
            if deployRelease == None:
                torDeployVersion = config.get("DMT", "rvScriptVer")
            else:
                torDeployVersion = config.get("DMT", "rvScriptVer_" + deployRelease)
            logger.info("Taking Deploy tar file version " + torDeployVersion + " from cfg file")
        else:
            torDeployVersion = options['tordeploy']
            logger.info("Taking Deploy tar file version " + torDeployVersion + " from user input")

        dmt.rv_deploy.deployTor(clusterId, drop, packageList, torDeployVersion, deployRelease, cfgTemplate)
