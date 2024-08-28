from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

import fem.utils

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Nodes"
    option_list = BaseCommand.option_list  + (
            make_option('--label',
                dest='lbl',
                help='name of the label to list nodes on'),
            )

    def handle(self, *args, **options):
        if options['lbl'] is None:
            raise CommandError("You need to provide a label")
        print fem.utils.getJenkinsSlavesByLabel(options['lbl'])

