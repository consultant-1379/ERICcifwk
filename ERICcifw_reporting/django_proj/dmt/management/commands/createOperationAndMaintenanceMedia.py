from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import fwk.utils 
import dmt.createOAMMedia
import sys, os, tempfile, logging, tarfile, subprocess

logger = logging.getLogger(__name__)

from ciconfig import CIConfig
config = CIConfig()


class Command(BaseCommand):
    '''
    '''
    help = "Build Operation and Maintenance Media from Nexus Tar Ball Prototype"
    option_list = BaseCommand.option_list  + (
            make_option('--artifactName',
                dest='artifactName',
                help='Artifact Name'),
            make_option('--artifactVersion',
                dest='artifactVersion',
                help='Artifact Version'),
            )

    def handle(self, *args, **options):
        '''
        '''
        if options['artifactName'] == None:
            raise CommandError("To run this option you need to specify the artifactName")
        if options['artifactVersion'] == None:
            raise CommandError("To run this option you need to specify the artifactVersion")
        artifactName = options['artifactName']
        artifactVersion = options['artifactVersion']

        try:
            localTmpDirectory,updatedLocalTmpDir = dmt.createOAMMedia.updateOAMArtifact(artifactName,artifactVersion)
            logger.info("Successfully created tmp area and media File")
        except Exception as e:
            logger.error("There was an issue setting up tmp area a media file: " +str(e))
            return 1
        try:
            logger.info("Successfully downloaded arrtifact from Nexus")
            dmt.createOAMMedia.getOAMArtifact(updatedLocalTmpDir,artifactName,artifactVersion)
        except Exception as e:
            logger.error("There was an issue getting artifact from Nexus: " +str(e))
            return 1
        try:
            dmt.createOAMMedia.unpackOAMArtifcat(localTmpDirectory,updatedLocalTmpDir,artifactName,artifactVersion) 
            logger.info("Successfully unpacked Artifact")
        except Exception as e:
            logger.error("Issue Unpacking Artifact: " +str(e))
            return 1
        try:
            dmt.createOAMMedia.createOAMISO(localTmpDirectory,artifactName,artifactVersion)
            logger.info("Succesfully Created ISO ")
        except Exception as e:
            logger.error("Issue creating ISO: " +str(e))




