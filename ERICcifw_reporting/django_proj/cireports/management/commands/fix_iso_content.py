from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
from cireports.models import *
import cireports.utils
from datetime import datetime
from ciconfig import CIConfig
import json
import os
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--isoName',
                dest='isoName',
                help='Name of the iso you wish to use'),
            make_option('--isoVersion',
                dest='isoVersion',
                help='The iso version to use'),
            make_option('--drop',
                dest='drop',
                help='The drop you wish'),
            make_option('--product',
                dest='product',
                help='The product the iso was built from'),
            make_option('--mediaContentFile',
                dest='mediaContentFile',
                help='The json media Content File .ie /tmp/mediaContent.json'),
            )
    def handle(self, *args, **options):
        if options['isoName'] != None:
            isoName = options['isoName']
        else:
            raise CommandError("Please specify a ISO Name")
        if options['isoVersion'] != None:
            isoVersion = options['isoVersion']
        else:
            raise CommandError("Please specify an ISO Version")
        if options['drop'] != None:
            drop = options['drop']
        else:
            raise CommandError("Please specify the drop of the ISO")
        if options['product'] != None:
            product = options['product']
        else:
            raise CommandError("Please specify the product the specified iso is built from")
        if options['mediaContentFile'] != None:
            mediaContentFile = options['mediaContentFile']
        else:
            raise CommandError("Please specify the json media Content File .ie /tmp/mediaContent.json, for the fix")
        if os.path.exists(mediaContentFile):
            try:
                dropObj = Drop.objects.get(name=drop, release__product__name=product)
                mediaArtifact = MediaArtifact.objects.get(name=isoName)
                isoObj = ISObuild.objects.get(version=isoVersion, mediaArtifact=mediaArtifact, drop=dropObj)
                ISObuildMapping.objects.filter(iso=isoObj).delete()
                IsotoDeliveryGroupMapping.objects.filter(iso=isoObj).delete()
                #create mediaContent.json with correct content for this version. Json file format: { "dropContents" : [contentData] }
                #To get contentData, check failed Jenkins ISO Build Job. Find in the console output  or in the mediaContent.txt in workspace.
                with open(mediaContentFile, 'r') as data_file:
                    decodedContent = json.loads(str(data_file.read()))
                for item in decodedContent['dropContents']:
                    contentObj = Package.objects.get(name=item['name'])
                    contentVersionObj = PackageRevision.objects.get(package=contentObj,version=item['version'],category__name=item['mediaCategory'])
                    drpObj = Drop.objects.get(name=item['deliveryDrop'], release__product__name=product)
                    cireports.utils.createMediaArtifactVersionToArtifactMapping(product, isoObj, drpObj, contentVersionObj, item['kgb'], item['testReport'], item['kgbSnapshotReport'])
                cireports.utils.addDeliveryGroupsToIso(isoObj)
                logger.info("ISO Content Fix is Complete")
            except Exception as e:
                raise CommandError("Issue updating Media Content - " + str(e))
        else:
            raise CommandError("Issue updating Media Content - could not find .json file")
