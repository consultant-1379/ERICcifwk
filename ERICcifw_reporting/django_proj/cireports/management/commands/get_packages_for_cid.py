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
            make_option('--drop',
                dest='drop',
                help='drop'),
            make_option('--product',
                dest='product',
                help='product'),
            )


    def handle(self, *args, **options):
        ret=cireports.utils.packagesForIntegratonPhase(options['drop'],options['product'])
        return ret


