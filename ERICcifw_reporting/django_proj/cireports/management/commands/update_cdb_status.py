from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
import sys
import logging
import cireports.models
import cireports.utils

from ciconfig import CIConfig
config = CIConfig()
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    option_list = BaseCommand.option_list  + (
            make_option('--drop',
                dest='drop',
                help='The drop name for the CDB run'),
            make_option('--product',
                dest='product',
                help='The product that the CDB is being tested against'),
            make_option('--type',
                dest='type',
                help='The CDB type (Virtual, Physical)'),
            make_option('--status',
                dest='status',
                help='The status of the CDB run (in_progress, passed, failed)'),
            make_option('--result',
                dest='result',
                help='The result of the CDB (html report link)'),
            make_option('--manifest',
                dest='manifest',
                help='A list/manifest of files that are on the ISO (used for OSS-RC product only)'),
            )

    def handle(self, *args, **options):
        if options['drop'] == None:
            raise CommandError("Drop option required")
        else:
            drop=options['drop']

        if options['product'] == None:
            raise CommandError("Product option required")
        else:
            product=options['product']

        if options['type'] == None:
            raise CommandError(" CDB Type is required")
        else:
           type=options['type']

        if options['status'] == None:
            raise CommandError("Status option required")
        else:
            status=options['status']

        result=options['result']
        manifest=options['manifest']
        
        cireports.utils.updateCDB(drop,product,type,status,result,manifest)
