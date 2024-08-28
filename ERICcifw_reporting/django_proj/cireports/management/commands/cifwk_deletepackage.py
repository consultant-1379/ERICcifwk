from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a package"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='package',
                help='name of the package to create'),
            make_option('--number',
                dest='number',
                help='package number (CXP1234567'),
            make_option('--resp',
                dest='resp',
                help='signum of the responsible individual'),
            )

    def handle(self, *args, **options):
        if options['package'] is None:
            raise CommandError("You need to provide a name for the package, in the form \"ERICxyz\"")
        if options['number'] is None:
            raise CommandError("You need to provide a number for the package, in the form \"CXP1234567\"")

        try:
            cireports.utils.deletePackage(options['package'], options['number'])
        except Exception as e:
            raise CommandError("Error deleting package - " + str(e))

