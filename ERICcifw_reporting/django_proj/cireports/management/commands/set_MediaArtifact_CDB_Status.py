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
            make_option('--mediaArtifact',
                dest='mediaArtifact',
                help='The MediaArtifact'),
            make_option('--ver',
                dest='ver',
                help='The MediaArtifact Version'),
            make_option('--status',
                dest='status',
                help='The status of the CDB run (in_progress, passed, failed)'),
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

        if options['mediaArtifact'] == None:
            raise CommandError("MediaArtifact required")
        else:
           mediaArtifact=options['mediaArtifact']

        if options['ver'] == None:
            raise CommandError("MediaArtifact version required")
        else:
            version=options['ver']

        if options['status'] == None:
            raise CommandError("Status option required")
        else:
            status=options['status']

        try:
            result = cireports.utils.updateMediaArtifactCDBStatus(drop,product,mediaArtifact,version,status)
        except Exception as e:
            result = "ERROR: " + str(e)

        return result

