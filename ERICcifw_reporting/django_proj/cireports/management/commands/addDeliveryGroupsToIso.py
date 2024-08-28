from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime
from django.core.exceptions import MultipleObjectsReturned
from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (make_option('--ver',dest='ver',help=''),)


    def handle(self, *args, **options):
        try:
            iso =  ISObuild.objects.get(version=options["ver"],drop__release__product__name="ENM",mediaArtifact__testware=0)
            result  = cireports.utils.addDeliveryGroupsToIso(iso)
            logger.info(str(result))
        except Exception as e:
            logger.error(str(e))
