from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import fem.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Collect job status information from Jenkins periodically"
    option_list = BaseCommand.option_list  + (
            make_option('--nbuilds',
                dest='nbuilds',
                help='maximum number of historical builds to collect data for'),
            )

    def handle(self, *args, **options):
        if options['nbuilds'] is not None:
            fem.utils.collectJobStatusInformation(int(options['nbuilds']))
        else:
            fem.utils.collectJobStatusInformation()

        #fem.utils.collectViewRelationships()

