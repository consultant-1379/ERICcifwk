from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import datetime
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Creating Release for a Product"
    option_list = BaseCommand.option_list  + (
            make_option('--product',dest='product',help=''),
            make_option('--releaseName',dest='releaseName',help=''),
            make_option('--dropName',dest='dropName',help=''),
            make_option('--planned',dest='planned',help=''),
            make_option('--actual',dest='actual',help=''),
            make_option('--mediaFreeze',dest='mediaFreeze',help=''),
            make_option('--designBase',dest='designBase',help=''),
            make_option('--systemInfo',dest='systemInfo',help=''),
            )

    def handle(self, *args, **options):
        product = options['product']

        releaseName = options['releaseName']
        self.stdout.write("ss:"+str(releaseName))

        product= options['product']
        releaseName = options['releaseName']
        dropName = options['dropName']
        planned = options['planned']
        actual= options['actual']
        mediaFreeze = options['mediaFreeze'] 
        designBase = options['designBase']
        systemInfo = options['systemInfo']

        try:
            productObj = Product.objects.get(name=product)
            releaseObj = Release.objects.get(name=releaseName,product=productObj)
            if designBase != None:
                designBaseObj = Drop.objects.get(release=releaseObj,name=designBase)
            else:
                designBaseObj = None
            now = datetime.datetime.now()
            plannedDate = now + datetime.timedelta(hours=int(planned)) 
            actualDate = now + datetime.timedelta(hours=int(actual)) 
            mediaFreezeDate = now + datetime.timedelta(hours=int(mediaFreeze))
            dropObj=Drop(name=dropName,release=releaseObj,planned_release_date=plannedDate,actual_release_date=actualDate, mediaFreezeDate=mediaFreezeDate, designbase=designBaseObj, systemInfo=systemInfo)
            dropObj.save()
            return "OK"
        except Exception as e:
            return "Error:" +str(e)
