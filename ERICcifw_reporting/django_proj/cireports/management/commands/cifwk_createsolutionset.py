from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

from cireports.models import *
import cireports.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Create a Solution Set"
    option_list = BaseCommand.option_list  + (
            make_option('--name',
                dest='solset',
                help='name of the solution set to create'),
            make_option('--number',
                dest='number',
                help='solution set product number (CXP1234567'),
            )

    def handle(self, *args, **options):
        if options['solset'] is None:
            raise CommandError("You need to provide a name for the solution set, in the form \"ERICxyz\"")
        if options['number'] is None:
            raise CommandError("You need to provide a number for the solution set, in the form \"CXP1234567\"")
        try:
            cireports.utils.createSolutionSet(options['solset'], options['number'])
        except cireports.utils.AlreadyExists as e:
            raise CommandError("Solution Set already exists - " + str(e))

