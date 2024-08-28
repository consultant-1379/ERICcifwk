from __future__ import print_function
from django.core.management.base import BaseCommand, CommandError
from optparse import make_option
from cireports.models import *
import cireports.utils 
import logging
config = CIConfig()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create the version of the Product Set"
    option_list = BaseCommand.option_list  + (
            make_option('--productSet',
                dest='productSet',
                help='The name of the product Set. e.g. TOR , OSS-RC'),
            make_option('--drop',
                dest='drop',
                help='The name of the drop. e.g. 3.0.S , 14.0.2'),
            )

    def handle(self, *args, **options):
        if options['productSet'] == None:
            raise CommandError("Product Set required")
        else:
            prodSet = options['productSet']
        if options['drop'] == None:
            raise CommandError("Drop required")
        else:
            drop = options['drop']

        try:
            version=cireports.utils.getOrCreateVersion(prodSet,drop)
            return "OK"
        except:
            return "Error"
