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
            make_option('--product',
                dest='product',
                help=''),
            )

    def handle(self, *args, **options):
        productName = options['product']
        try:
            productObj = Product(name=productName)
            productObj.save()
            return "OK"
        except:
            return "Error"
