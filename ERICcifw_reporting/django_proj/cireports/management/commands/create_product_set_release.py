from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create the content for the ISO, will build up content for latest drop unless a drop is specified"
    option_list = BaseCommand.option_list  + (
            make_option('--productSet',dest='productSet',help=''),
            make_option('--productSetReleaseName',dest='productSetReleaseName',help=''),
            make_option('--releaseNumber',dest='releaseNumber',help=''),
            make_option('--release',dest='release',help=''),
            make_option('--mediaArtifact',dest='mediaArtifact',help=''),
            make_option('--updateMasterStatus',dest='updateMasterStatus',help=''),
            )

    def handle(self, *args, **options):
        productSet = options['productSet']
        productSetReleaseName = options['productSetReleaseName']
        mediaArtifact = options['mediaArtifact']
        release = options['release']
        number = options['releaseNumber']
        if options['updateMasterStatus'] == 0:
            updateMasterStatus=False
        else:
            updateMasterStatus=True
        try:
            productSetObj = ProductSet.objects.get(name=productSet)
            releaseObj = Release.objects.get(name=release)
            mediaObj = MediaArtifact.objects.get(name=mediaArtifact)
            psRelObj = ProductSetRelease(updateMasterStatus=updateMasterStatus,masterArtifact=mediaObj,name=productSetReleaseName,release=releaseObj,number=number,productSet=productSetObj) 
            psRelObj.save()
            return "OK"
        except Exception as e:
            return "Error:" +str(e)
