from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from ciconfig import CIConfig
import dmt.uploadContent
from dmt.models import *

import sys, os, tempfile, shutil

import logging

logger = logging.getLogger(__name__)
osid = os.getpid()
config = CIConfig()

#Instanstate a file name, file will be used to contain ssh tunnel process id
class Command(BaseCommand):
    '''
    The purpose of this class is to upload a pre-populated SED into the cluster specified
    '''
    help = "The purpose of this script is to upload a pre-populated SED into the cluster specified"
    option_list = BaseCommand.option_list  + (
            make_option('--clusterid',
                dest='clusterId',
                help='ID of the Cluster to be configured'),
            make_option('--setSED',
                dest='setSED',
                help='Optional Parameter: To Specify a specific sed template'),
            make_option('--uploadFile',
                dest='uploadFile',
                help='Location of pre populated SED file'),
            )

    def handle(self, *args, **options):

        #Define the cluster id if not set check if a group is set if not throw an error
        if options['clusterId'] == None:
            if options['installGroup'] == None:
                raise CommandError("You need to specify either cluster group or cluster ID")
            else:
                clusterId = dmt.utils.getFreeCluster(options['installGroup'])
        else:
            clusterId = options['clusterId']

        if options['setSED'] != None:
            setSED = options['setSED']
        else:
            raise CommandError("You need to specify the version of the SED to use to populate the info with")

        if options['uploadFile'] != None:
            uploadFile = options['uploadFile']
        else:
            raise CommandError("You need to specify the pre populated SED file for upload")

        dmt.uploadContent.uploadContentMain(clusterId, setSED, uploadFile)
