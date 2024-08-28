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
            make_option('--product',dest='product',help=''),
            make_option('--releaseName',dest='releaseName',help=''),
            make_option('--track',dest='track',help=''),
            make_option('--isoArtifact',dest='isoArtifact',help=''),
            make_option('--isoGroupId',dest='isoGroupId',help=''),
            make_option('--isoArmRepo',dest='isoArmRepo',help=''),
            make_option('--mediaArtifact',dest='mediaArtifact',help=''),
            )

    def handle(self, *args, **options):
        product = options['product']

        releaseName = options['releaseName']

        track = options['track']
        isoArtifact = options['isoArtifact']
        isoGroupId = options['isoGroupId']
        isoArmRepo = options['isoArmRepo']
        mediaArtifact = options['mediaArtifact']
        try:
            productObj = Product.objects.get(name=product)
            mediaObj = MediaArtifact.objects.get(name=mediaArtifact)
            relObj = Release(masterArtifact=mediaObj,name=releaseName,track=track,product=productObj,iso_artifact=isoArtifact,iso_groupId=isoGroupId,iso_arm_repo=isoArmRepo) 
            relObj.save()
            return "OK"
        except Exception as e:
            return "Error:" +str(e)
