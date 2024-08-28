from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils
from datetime import datetime
from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--isoName',
                dest='isoName',
                help='Name of the iso you wish to use to populate the given drop'),
            make_option('--isoVersion',
                dest='isoVersion',
                help='The iso version to use to populate the drop'),
            make_option('--drop',
                dest='drop',
                help='The drop you wish to populate with the given content'),
            make_option('--product',
                dest='product',
                help='The product the iso was built from'),
            )


    def handle(self, *args, **options):
        if options['isoName'] != None:
            isoName = options['isoName']
        else:
            raise CommandError("Please specify a ISO Name to use to populate the drop")
        if options['isoVersion'] != None:
            isoVersion = options['isoVersion']
        else:
            raise CommandError("Please specify an ISO Version to use to populate the drop")
        if options['drop'] != None:
            drop = options['drop']
        else:
            raise CommandError("Please specify the drop that should be populated")
        if options['product'] != None:
            product = options['product']
        else:
            raise CommandError("Please specify the product the specified iso is built from")
        cireports.utils.deliveryIsoContentToDrop(isoName,isoVersion,drop,product)

